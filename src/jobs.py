"""Checkpoint orchestration around the existing Whisper implementations."""
from i18n import tr
from dataclasses import asdict
from pathlib import Path
from datetime import datetime

from mixed_language import MixedConfig, MIXED_LANGUAGE, speech_chunks, transcribe_mixed, offset_segment
from project import Project, fingerprint
from speech_models import LocalAdapter, SAMPLE_RATE, hardware_error, checked_segments


def job_settings(model_name, language):
    return dict(pipeline=2, model=model_name, language=language, beam_size=5,
                task='transcribe', word_timestamps=True, condition_on_previous_text=False,
                segmentation=asdict(MixedConfig()))


def segment_data(item):
    return dict(start=item.start, end=item.end, text=item.text.strip(),
        language=getattr(item, 'language', None),
        language_confidence=getattr(item, 'language_confidence', None),
        words=[dict(start=w.start, end=w.end, word=w.word, probability=getattr(w, 'probability', None))
               for w in (getattr(item, 'words', None) or [])], speaker='')


def transcribe_chunk(model, chunk, language, previous, config, start, stop, decoding=None):
    detected = language
    if language == MIXED_LANGUAGE:
        items, _ = transcribe_mixed(model, None, stop, config, True, audio=chunk,
            speech_spans=[dict(start=0, end=len(chunk))], previous_language=previous, log_offset=start/SAMPLE_RATE,
            decode_options=decoding.get('transcribe') if decoding else None)
    elif isinstance(model, LocalAdapter):
        items = checked_segments(model.infer(chunk), 0, len(chunk) / SAMPLE_RATE)
    else:
        options = decoding['transcribe'] if decoding else dict(task='transcribe',
            beam_size=5, vad_filter=False, word_timestamps=True, condition_on_previous_text=False)
        items, info = model.transcribe(chunk, language=language, **options)
        detected = info.language
    saved = []
    # Exhaust the lazy iterator before committing anything, including mixed mode.
    for item in items:
        if stop.is_set():
            break
        selected = getattr(item, 'language', language or detected)
        shifted = offset_segment(item, start / SAMPLE_RATE, len(chunk) / SAMPLE_RATE,
                                 selected, getattr(item, 'language_confidence', None))
        if shifted.text.strip():
            if shifted.end <= shifted.start:
                raise ValueError(tr('jobs.transcribe_chunk.the_model_returned_text_without_a_valid_time_interval'))
            saved.append(segment_data(shifted))
    return saved


def transcribe_job(model, source, target, settings, stop, emit, resume=False, recover_gpu=None, selected_device='cpu'):
    from pcm_audio import decode_audio, speech_spans
    from faster_whisper.vad import VadOptions
    with Project(target, create=not resume) as project:
        def export_original():
            for warning in project.export(view='original'):
                emit('log', warning)

        project.begin_preparation(source, settings)
        from decode_settings import apply_settings, runtime_settings
        decoding = settings.get('decoding')
        apply_settings(model, decoding)
        def record_runtime():
            runtime = runtime_settings(model, selected_device)
            runtime['legacy_decoding_unknown'] = decoding is None
            history = project.get('execution_history', [])
            if not history or history[-1]['runtime'] != runtime:
                if history:
                    emit('log', tr('revision.runtime_changed'))
                with project.db:
                    project.put('execution_history', history + [dict(next_chunk=project.get('next_chunk', 0), runtime=runtime)])
        preparing = project.phase() == 'preparing'
        emit('status', tr('jobs.transcribe_job.preparing_audio_checking_the_recording'))
        if preparing:
            project.preparation_stage('hashing')
        if stop.is_set():
            return False
        before = Path(source).stat()
        try:
            digest = fingerprint(source, stop)
        except InterruptedError:
            if stop.is_set():
                return False
            raise
        if stop.is_set():
            return False
        if not preparing:
            project.verify(digest, settings)
            if project.get('complete'):
                export_original()
                return True
        else:
            saved_digest = project.get('fingerprint')
            if saved_digest is not None and saved_digest != digest:
                raise ValueError(tr('jobs.transcribe_job.the_recording_does_not_match_the_saved_project_start'))
            project.preparation_stage('decoding', digest)
        emit('status', tr('jobs.transcribe_job.preparing_audio_decoding_the_recording'))
        audio = None
        try:
            audio = decode_audio(str(source), sampling_rate=SAMPLE_RATE, folder=Path(target)/'.pcm-cache', stop=stop)
            after = Path(source).stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError(tr('jobs.transcribe_job.the_source_recording_changed_during_preparation_start_a_new'))
            if stop.is_set():
                return False
            config = MixedConfig(**settings['segmentation'])
            if not preparing:
                plan = project.get('plan')
                if len(audio) != project.get('samples'):
                    raise ValueError(tr('jobs.transcribe_job.decoded_audio_length_changed_start_a_new_transcription'))
            else:
                project.preparation_stage('vad')
                emit('status', tr('jobs.transcribe_job.preparing_audio_detecting_speech'))
                spans = speech_spans(audio, VadOptions(max_speech_duration_s=config.max_speech_segment_duration,
                    min_silence_duration_ms=config.min_silence_duration_ms, speech_pad_ms=config.speech_pad_ms), stop)
                if stop.is_set():
                    return False
                plan = list(speech_chunks(spans, len(audio), config))
                if stop.is_set():
                    return False
                project.initialize(source, digest, settings, plan, len(audio))
            language = settings['language']
            previous = project.get('previous_language')
            next_chunk = project.get('next_chunk')
            record_runtime()
            project.start_transcription()
            emit('status', tr('jobs.transcribe_job.transcribing_speech'))
            emit('progress', 100 * (plan[next_chunk-1][1] / max(1, len(audio))) if next_chunk else 0)
            for index in range(next_chunk, len(plan)):
                if stop.is_set():
                    export_original()
                    return False
                start, end = plan[index]
                chunk = audio[start:end]
                try:
                    saved = transcribe_chunk(model, chunk, language, previous, config, start, stop, decoding)
                except Exception as exc:
                    export_original()
                    if selected_device != 'cuda' or not hardware_error(exc) or recover_gpu is None:
                        raise
                    # The current chunk is uncommitted. All earlier chunks stay intact.
                    import traceback
                    traceback.clear_frames(exc.__traceback__)
                    model = None
                    model = recover_gpu(exc)
                    selected_device = 'cpu'
                    apply_settings(model, decoding)
                    record_runtime()
                    saved = transcribe_chunk(model, chunk, language, previous, config, start, stop, decoding)
                if stop.is_set():
                    # Entire unfinished chunk is retried. Never checkpoint a partial decoder iterator.
                    export_original()
                    return False
                if saved:
                    previous = saved[-1]['language']
                project.commit_chunk(index, saved, previous)
                for segment in saved:
                    emit('segment', segment)
                emit('progress', min(99, end / max(1, len(audio)) * 100))
            emit('status', tr('jobs.transcribe_job.saving_the_completed_transcript_and_subtitles'))
            project.finish()
            export_original()
            emit('progress', 100)
            return True
        except InterruptedError:
            if stop.is_set():
                return False
            raise
        finally:
            if hasattr(audio, 'close'):
                audio.close()

def reserve_output(folder, stem):
    """Každá nahrávka má vlastný priečinok; nikdy neprepíše starší prepis."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    base = stem[:100] + '_' + datetime.now().strftime('%Y%m%d_%H%M%S')
    for n in range(10000):
        target = folder / (base if not n else f'{base}_{n}')
        try:
            target.mkdir()
            return target
        except FileExistsError:
            pass
    raise OSError(tr('prepis.reserve_output.cannot_create_a_unique_transcript_folder'))

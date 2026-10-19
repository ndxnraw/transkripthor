"""Batch orchestration, owned exclusively by the ASR child process."""
import threading
import time
from pathlib import Path
from i18n import tr
from speech_models import ModelManager, GPUError
from project import Project
from jobs import job_settings, transcribe_job
from jobs import reserve_output


def recording_duration(source):
    """Cheap container estimate; decoding later supplies the exact sample count."""
    import av
    try:
        with av.open(str(source)) as container:
            stream = next(iter(container.streams.audio), None)
            if stream is not None and stream.duration is not None and stream.time_base is not None:
                return float(stream.duration * stream.time_base)
            if stream is not None and container.duration is not None:
                return container.duration / av.time_base
    except (OSError, ValueError):
        pass  # An unknown duration must not prevent the normal file error path.
    return None


class BatchRunner:
    def __init__(self, config, stop, events):
        self.__dict__.update(config)
        self.stop, self.events = stop, events
        self.models = ModelManager()
        self.model = None

    def request_cpu(self, exc, emit):
        emit('log', f'GPU: {type(exc).__name__}: {exc}')
        ack, answer = threading.Event(), []
        emit('cpu_request', (ack, answer))
        deadline = time.monotonic() + 120
        while not ack.wait(.1):
            if time.monotonic() > deadline:
                raise TimeoutError(tr('asr.ack_timeout'))
            if self.stop.is_set():
                raise InterruptedError(tr('prepis.request_cpu.cpu_fallback_cancelled'))
        if self.stop.is_set() or not answer or not answer[0]:
            self.stop.set()
            raise InterruptedError(tr('prepis.request_cpu.cpu_fallback_cancelled_saved_segments_were_preserved'))

    def work(self, files, folder, language, model_name, offline, selected_device='cpu'):
        emit = lambda kind, value: self.events.put((kind, value))
        def update(identifier, **changes):
            ack = threading.Event()
            result = []
            emit('job', (identifier, changes, ack, result))
            if not ack.wait(15):
                raise TimeoutError(tr('asr.ack_timeout'))
            if not result or not result[0]:
                raise OSError(tr('prepis.update.could_not_save_the_queue_safely_check_the_output'))
        done = failed = 0
        current = None
        requested_language, requested_model = language, model_name
        try:
            emit('phase', 'probing')
            for identifier, file in zip(self.batch_ids, files):
                if self.stop.is_set():
                    break
                emit('duration', (identifier, recording_duration(file)))
            from model_catalog import ensure_model, cached_path
            def load():
                emit('phase', 'loading')
                emit('device', tr('prepis.load.waiting_for_model_loading'))
                self.model = None  # Let ModelManager release a different snapshot before allocating another.
                self.model = self.models.get(language, model_name, self.cache, True, emit, self.stop, selected_device, revision=revision)
                from speech_models import LocalAdapter
                actual = self.model.device if isinstance(self.model, LocalAdapter) else self.model.model.device
                emit('device', 'GPU (CUDA)' if actual == 'cuda' else 'CPU')
                return self.model
            def recover(exc):
                nonlocal selected_device
                self.request_cpu(exc, emit)
                selected_device = 'cpu'
                self.model = None
                self.models.close()
                return load()
            for i, file in enumerate(files, 1):
                if self.stop.is_set():
                    break
                identifier = self.batch_ids[i-1]
                current = next(item for item in self.items if item['id'] == identifier)
                emit('batch_index', i-1)
                emit('phase', 'preparing')
                emit('progress', 0)
                emit('log', '\n' + Path(file).name)
                try:
                    target = current.get('project') if self.batch_mode != 'new' else ''
                    resume = False
                    settings = None
                    if target and (Path(target) / 'projekt.sqlite3').is_file():
                        with Project(target) as project:
                            resume = project.get('schema') == 1
                            if resume:
                                settings = project.get('settings')
                    if settings is not None:
                        language, model_name = settings['language'], settings['model']
                        revision = settings.get('model_revision')
                        if revision is None:
                            raise ValueError(tr('revision.unknown'))
                        if 'decoding' not in settings:
                            emit('log', tr('revision.legacy'))
                    else:
                        language, model_name = requested_language, requested_model
                        revision = None
                    try:
                        ensure_model(self.cache, model_name, offline, emit, self.stop, revision=revision)
                    except Exception as exc:
                        if revision is not None and not isinstance(exc, InterruptedError):
                            raise RuntimeError(tr('revision.missing', model=model_name, revision=revision) + '\n' + str(exc)) from exc
                        raise
                    revision = cached_path(self.cache, model_name, revision).name
                    try:
                        load()
                    except GPUError as exc:
                        recover(exc)
                    if settings is None:
                        from decode_settings import effective_settings
                        settings = job_settings(model_name, language)
                        settings.update(model_revision=revision, decoding=effective_settings(self.model))
                    if not target:
                        target = str(reserve_output(folder, Path(file).stem))
                    update(identifier, state='processing', project=str(target), error='')
                    def file_emit(kind, value):
                        emit(kind, (identifier, value) if kind == 'duration' else value)
                    complete = transcribe_job(self.model, file, target, settings,
                                              self.stop, file_emit, resume=resume, recover_gpu=recover, selected_device=selected_device)
                    update(identifier, state='completed' if complete else 'interrupted')
                    done += int(complete)
                    emit('log', f'{tr('prepis.work.saved') if complete else tr('prepis.work.partial_transcript')}: {target}')
                except InterruptedError:
                    update(identifier, state='interrupted')
                    break
                except Exception as exc:
                    failed += 1
                    update(identifier, state='failed', error=str(exc))
                    emit('log', tr('prepis.work.file_error', p0=Path(file).name, p1=exc))
            emit('status', tr('prepis.work.completed_errors', p0=tr('prepis.work.stopped') if self.stop.is_set() else tr('prepis.work.completed'), p1=done, p2=len(files), p3=failed))
        except InterruptedError:
            emit('status', tr('prepis.work.loading_interrupted'))
        except Exception as exc:
            if current is None:
                for identifier in self.batch_ids:
                    update(identifier, state='failed', error=str(exc))
            emit('status', tr('prepis.work.could_not_start_transcription'))
            emit('error', str(exc) + tr('prepis.work.allow_model_downloads_on_first_use_turn_off_offline'))
        finally:
            self.model = None
            self.models.close()
            emit('finished', None)

"""Lokálne modely s rovnakým segmentovým rozhraním ako faster-whisper."""
from i18n import tr
import gc
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace

SLOVAK_MODEL = 'kinit/whisper-large-v3-sk'
SAMPLE_RATE = 16000
DEVICES = {'CPU – kompatibilný režim': 'cpu', 'GPU (CUDA) – NVIDIA': 'cuda'}

class GPUError(RuntimeError):
    pass

def route(language, selected):
    if selected == SLOVAK_MODEL and language != 'sk':
        raise ValueError(tr('speech_models.route.the_kinit_model_only_supports_slovak_select_slovak_or'))
    return selected

def device(model_id=SLOVAK_MODEL):
    if model_id != SLOVAK_MODEL:
        try:
            import ctranslate2
            return 'cuda' if ctranslate2.get_cuda_device_count() else 'cpu'
        except (ImportError, OSError, RuntimeError):
            return 'cpu'
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    except (ImportError, OSError):
        return 'cpu'

def hardware_error(exc):
    return isinstance(exc, MemoryError) or any(word in str(exc).lower() for word in
        ('out of memory', 'cuda', 'cudnn', 'cublas', 'allocation', 'not compiled with'))

def release_memory():
    gc.collect()
    try:
        torch = sys.modules.get('torch')
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
    except (ImportError, OSError, RuntimeError):
        pass

def checked_segments(items, offset, duration):
    """Neodhadovať chýbajúce časové značky; chybu ponechať viditeľnú."""
    result = []
    last = 0.0
    for item in items:
        text = str(item['text']).strip()
        if not text:
            continue
        start, end = item['start'], item['end']
        if start is None or end is None:
            raise RuntimeError(tr('speech_models.checked_segments.the_model_did_not_return_complete_timestamps_try_the'))
        start, end = float(start), float(end)
        if not math.isfinite(start + end) or start < 0 or end < start or start < last:
            raise RuntimeError(tr('speech_models.checked_segments.the_model_returned_invalid_timestamps'))
        start, end = min(start, duration), min(end, duration)
        last = start
        words = checked_segments(item.get('words', []), offset, duration)
        for word in words:
            word.word = word.text
        result.append(SimpleNamespace(start=offset + start, end=offset + end, text=text, words=words))
    return result

class LocalAdapter:
    def __init__(self, model_id, cache, offline, selected_device, emit, stop, snapshot=None):
        self.model_id = model_id
        self.cache = Path(cache)
        self.offline = offline
        self.device = selected_device
        self.emit = emit
        self.stop = stop
        self.snapshot = snapshot
        self.model = self.processor = self.pipe = None
        self.load()

    def close(self):
        self.pipe = self.model = self.processor = None

    def transcribe(self, source, language=None, **kwargs):
        # Rovnaké PyAV dekódovanie, mono 16 kHz a Silero VAD ako pôvodný engine.
        from pcm_audio import decode_audio, speech_spans
        from faster_whisper.vad import VadOptions
        audio = decode_audio(source, sampling_rate=SAMPLE_RATE, stop=self.stop)
        duration = len(audio) / SAMPLE_RATE
        def generate():
            if self.stop.is_set() or not len(audio):
                return
            spans = speech_spans(audio, VadOptions(max_speech_duration_s=28, speech_pad_ms=200), self.stop)
            for span in spans:
                # Pevná horná hranica aj pri zmene implementácie VAD.
                for start in range(span['start'], span['end'], 28 * SAMPLE_RATE):
                    if self.stop.is_set():
                        return
                    end = min(span['end'], start + 28 * SAMPLE_RATE)
                    chunk = audio[start:end]
                    try:
                        items = self.infer(chunk)
                    except Exception as exc:
                        raise RuntimeError(tr('speech_models.generate.transcription_failed_select_a_smaller_model_if_memory_is', p0=self.model_id, p1=exc)) from exc
                    # Výsledok celého kroku sa overí pred emitovaním: žiadne duplikáty pri GPU retry.
                    for segment in checked_segments(items, start / SAMPLE_RATE, len(chunk) / SAMPLE_RATE):
                        if self.stop.is_set():
                            return
                        yield segment
        def managed():
            try:
                yield from generate()
            finally:
                if hasattr(audio, 'close'):
                    audio.close()
        return managed(), SimpleNamespace(language=language, duration=duration)

class SlovakWhisper(LocalAdapter):
    def load(self):
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
        hub = str(self.cache / 'huggingface')
        opts = dict(cache_dir=hub, local_files_only=self.offline, trust_remote_code=False)
        source = getattr(self, 'snapshot', None) or self.model_id
        if not getattr(self, 'snapshot', None):
            opts['revision'] = 'v2.0'
        if self.device == 'cpu':
            torch.set_num_threads(max(1, min(4, (os.cpu_count() or 2) - 1)))
        self.processor = AutoProcessor.from_pretrained(source, **opts)
        dtype = torch.float16 if self.device == 'cuda' else torch.float32
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            source, torch_dtype=dtype, use_safetensors=True,
            attn_implementation='eager', **opts).to(self.device).eval()
        self.pipe = pipeline('automatic-speech-recognition', model=self.model,
            tokenizer=self.processor.tokenizer, feature_extractor=self.processor.feature_extractor,
            device=0 if self.device == 'cuda' else -1, torch_dtype=dtype)

    def infer(self, audio):
        import torch
        kwargs = {'language': 'sk', 'task': 'transcribe'}
        if getattr(self, 'decode_profile', None):
            from transformers import GenerationConfig
            kwargs['generation_config'] = GenerationConfig.from_dict(self.decode_profile['generation_config'])
            kwargs.update(self.decode_profile['generate_kwargs'])
        with torch.inference_mode():
            result = self.pipe({'raw': audio, 'sampling_rate': SAMPLE_RATE},
                return_timestamps='word', generate_kwargs=kwargs)
        if result.get('text', '').strip() and not result.get('chunks'):
            raise RuntimeError(tr('speech_models.infer.whisper_did_not_return_timestamps'))
        # Word alignment supplies the final boundary even when the decoder omits
        # its closing segment token. Group words without inventing timestamps.
        words = [dict(text=item['text'], start=item['timestamp'][0], end=item['timestamp'][1])
                 for item in result.get('chunks', [])]
        checked_segments(words, 0, len(audio) / SAMPLE_RATE)
        segments = []
        for word in words:
            text = word['text'].strip()
            if not text:
                continue
            if not segments or segments[-1]['text'].endswith(('.', '?', '!')) or \
                    word['end'] - segments[-1]['start'] > 7:
                segments.append(dict(text=text, start=word['start'], end=word['end'], words=[word]))
            else:
                segments[-1]['text'] += ' ' + text
                segments[-1]['end'] = word['end']
                segments[-1]['words'].append(word)
        return segments

def load_backend(model_id, cache, offline, selected_device, emit, stop, snapshot=None):
    cls = {SLOVAK_MODEL: SlovakWhisper}.get(model_id)
    if cls:
        # Oddeliť konštrukciu od load(), aby bolo možné uvoľniť aj čiastočne načítané modely.
        adapter = cls.__new__(cls)
        try:
            cls.__init__(adapter, model_id, cache, offline, selected_device, emit, stop, snapshot=snapshot)
            return adapter
        except Exception:
            adapter.close()
            raise
    from faster_whisper import WhisperModel
    return WhisperModel(str(snapshot) if snapshot else model_id, device=selected_device,
        compute_type='float16' if selected_device == 'cuda' else 'int8',
        download_root=str(cache), local_files_only=offline)

class ModelManager:
    """Jeden aktívny model: opätovné použitie medzi súbormi, obmedzená RAM/VRAM."""
    def __init__(self):
        self.model = self.key = None

    def get(self, language, selected_model, cache, offline, emit, stop, selected_device='cpu', revision=None):
        try:
            return self._get(language, selected_model, cache, offline, emit, stop, selected_device, revision)
        except BaseException:
            self.close()
            raise

    def _get(self, language, selected_model, cache, offline, emit, stop, selected_device, revision=None):
        requested = route(language, selected_model)
        if stop.is_set():
            raise InterruptedError(tr('speech_models.get.loading_interrupted'))
        # Jazyk nemení váhy viacjazyčného Whisperu; nevyžaduje opätovné načítanie.
        selected = selected_device if selected_device in ('cpu', 'cuda') else 'cpu'
        key = (requested, str(Path(cache).resolve()), selected, revision)
        if key == self.key and self.model is not None:
            if isinstance(self.model, LocalAdapter):
                self.model.stop, self.model.emit = stop, emit
            return self.model
        self.close()
        from ownership import Lease
        self.lease = Lease(Path(cache)/'.models.lock')
        snapshot = None
        if revision is not None:
            from model_catalog import cached_path
            snapshot = cached_path(cache, requested, revision)
            if snapshot is None:
                raise ValueError(tr('revision.offline', model=requested, revision=revision))
        errors = []
        for target in [selected]:
            try:
                if target == 'cuda' and device(requested) != 'cuda':
                    raise GPUError(tr('speech_models.get.cuda_is_unavailable_on_this_computer'))
                emit('status', tr('speech_models.get.loading_model_into_memory', p0=requested, p1=target))
                options = dict(snapshot=str(snapshot)) if snapshot is not None else {}
                model = load_backend(requested, cache, offline, target, emit, stop, **options)
                if stop.is_set():
                    if isinstance(model, LocalAdapter):
                        model.close()
                    del model
                    release_memory()
                    raise InterruptedError(tr('speech_models.get.loading_interrupted'))
                self.model, self.key = model, key
                emit('log', tr('speech_models.get.active_model_device', p0=requested, p1=target))
                return model
            except InterruptedError:
                raise
            except Exception as exc:
                errors.append(f'{requested} ({target}): {exc}')
                emit('log', errors[-1])
                release_memory()
                if stop.is_set():
                    raise InterruptedError(tr('speech_models.get.loading_interrupted')) from exc
                if target == 'cuda' and hardware_error(exc):
                    raise GPUError(str(exc)) from exc
                if target != 'cuda' or not hardware_error(exc):
                    break
        raise RuntimeError(tr('speech_models.get.could_not_load_the_selected_model_check_cache_and') + '\n'.join(errors))

    def close(self):
        if isinstance(self.model, LocalAdapter):
            self.model.close()
        self.model = self.key = None
        release_memory()
        if getattr(self, 'lease', None):
            self.lease.close()
            self.lease = None

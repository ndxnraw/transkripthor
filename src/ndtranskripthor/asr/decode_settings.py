"""Serializable backend-specific decoding contracts, independent of UI/device."""
import inspect
import json
from ndtranskripthor.core.i18n import tr
from importlib.metadata import version, PackageNotFoundError
from ndtranskripthor.asr.speech_models import LocalAdapter


def effective_settings(model):
    if isinstance(model, LocalAdapter):
        return dict(backend='transformers-whisper', generation_config=model.model.generation_config.to_dict(),
            generate_kwargs=dict(language='sk', task='transcribe', num_beams=5, do_sample=False,
                                 condition_on_prev_tokens=False), return_timestamps='word')
    parameters = {}
    from faster_whisper import WhisperModel
    for name, value in inspect.signature(WhisperModel.transcribe).parameters.items():
        if name not in ('audio', 'language') and value.default is not inspect.Parameter.empty:
            try:
                parameters[name] = json.loads(json.dumps(value.default))
            except (ValueError, TypeError):
                continue
    parameters.update(task='transcribe', beam_size=5, vad_filter=False,
                      word_timestamps=True, condition_on_previous_text=False)
    return dict(backend='faster-whisper', transcribe=parameters)


def apply_settings(model, profile):
    if profile is None:
        if isinstance(model, LocalAdapter):
            model.decode_profile = None  # Preserve legacy model-config defaults.
        return
    expected = 'transformers-whisper' if isinstance(model, LocalAdapter) else 'faster-whisper'
    if profile['backend'] != expected:
        raise ValueError(tr('revision.backend_mismatch'))
    if isinstance(model, LocalAdapter):
        model.decode_profile = profile


def runtime_settings(model, device):
    local = isinstance(model, LocalAdapter)
    versions = {}
    for package in (('torch', 'transformers') if local else ('faster-whisper', 'ctranslate2')):
        try: versions[package] = version(package)
        except PackageNotFoundError: versions[package] = 'unavailable'
    compute = 'float16' if device == 'cuda' else 'float32' if local else 'int8'
    actual = getattr(getattr(model, 'model', None), 'compute_type', None) if not local else None
    return dict(device=device, compute_type=actual if isinstance(actual, str) else compute,
                requested_compute_type=compute, libraries=versions)

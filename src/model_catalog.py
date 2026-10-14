"""Model inventory and explicit, local-cache-only management."""
from i18n import tr
import json
import shutil
from pathlib import Path
from speech_models import SLOVAK_MODEL

SPEAKER_MODEL = 'Wespeaker/wespeaker-voxceleb-resnet34-LM'
SPEAKER_REVISION = 'f0c48c298fd835726c27956a5d617bad7115627e'
DESCRIPTIONS = {
    'tiny': 'model_catalog.labels.quick_test_lower_accuracy', 'small': 'model_catalog.labels.balanced_speed_and_memory_use',
    'medium': 'model_catalog.labels.higher_accuracy_more_ram', 'large-v3': 'model_catalog.labels.highest_requirements_also_suitable_for_cz_sk',
    SLOVAK_MODEL: 'model_catalog.labels.slovak_only_about_gb_of_weights_high_ram_requirements',
    SPEAKER_MODEL: 'model_catalog.labels.optional_voices_cpu_cc_by_no_token_required_does'}


def location(cache, model):
    if model not in DESCRIPTIONS:
        raise ValueError(tr('model_catalog.location.unknown_model'))
    repo = model if '/' in model else 'Systran/faster-whisper-' + model
    base = Path(cache) / 'huggingface' if model in (SLOVAK_MODEL, SPEAKER_MODEL) else Path(cache)
    revision = 'v2.0' if model == SLOVAK_MODEL else SPEAKER_REVISION if model == SPEAKER_MODEL else 'main'
    return base, repo, revision


def cache_folder(cache, model):
    base, repo, _ = location(cache, model)
    return base / ('models--' + repo.replace('/', '--'))


def complete_snapshot(path, model, verify_receipt=True):
    try:
        required = ['voxceleb_resnet34_LM.onnx'] if model == SPEAKER_MODEL else ['config.json', 'tokenizer.json']
        if model == SLOVAK_MODEL:
            required += ['preprocessor_config.json']
            if (path/'model.safetensors').is_file():
                required += ['model.safetensors']
            else:
                index=json.loads((path/'model.safetensors.index.json').read_text(encoding='utf-8'))
                shards=set(index['weight_map'].values())
                if not shards:
                    return False
                required += ['model.safetensors.index.json'] + list(shards)
        elif model != SPEAKER_MODEL:
            required += ['model.bin']
        for name in required:
            from download_worker import checked_name
            checked_name(name)
            file=path/name
            if not file.is_file() or file.stat().st_size <= 0:
                return False
            if name.endswith('.json'):
                if not isinstance(json.loads(file.read_text(encoding='utf-8')),dict):
                    return False
        receipt=path/'.nd-verified.json'
        if verify_receipt and receipt.exists():
            data=json.loads(receipt.read_text(encoding='utf-8'))
            if not data.get('complete') or not set(required) <= data['files'].keys():
                return False
            for name, meta in data['files'].items():
                checked_name(name)
                stat=(path/name).stat()
                if stat.st_size != meta['size'] or stat.st_mtime_ns != meta['mtime']:
                    return False
        return True
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        return False


def checked_revision(revision):
    import re
    if not isinstance(revision, str) or not re.fullmatch('[a-f0-9]{40}', revision):
        raise ValueError(tr('revision.invalid'))
    return revision


def cached_path(cache, model, revision=None):
    folder = cache_folder(cache, model)
    if revision is not None:
        path = folder / 'snapshots' / checked_revision(revision)
        return path if complete_snapshot(path, model) else None
    _, _, revision = location(cache, model)
    ref = folder / 'refs' / revision
    commit = ref.read_text().strip() if ref.is_file() else revision
    if not commit or '/' in commit or '\\' in commit or ':' in commit or commit in ('.','..'):
        return None
    path = folder / 'snapshots' / commit
    return path if complete_snapshot(path, model) else None


def inventory(cache):
    result = []
    for model, description in DESCRIPTIONS.items():
        folder = cache_folder(cache, model)
        # Count physical files once when snapshots use symlinks.
        seen, size = set(), 0
        for path in folder.rglob('*') if folder.exists() else []:
            if path.is_file():
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    size += path.stat().st_size
        result.append(dict(model=model, available=cached_path(cache, model) is not None,
                           size=size, description=tr(description)))
    return result


def download(cache, model, emit, stop, revision=None):
    from download_transport import supervise
    from ownership import Lease
    with Lease(Path(cache)/'.models.lock'):
        if revision is None:
            supervise(cache, model, emit, stop)
        else:
            supervise(cache, model, emit, stop, revision=checked_revision(revision))


def ensure_model(cache, model, offline, emit, stop, revision=None):
    if cached_path(cache, model, revision):
        return
    if revision is not None and offline:
        raise ValueError(tr('revision.offline', model=model, revision=revision))
    if offline:
        raise ValueError(tr('model_catalog.ensure_model.the_selected_model_is_not_fully_available_locally_turn'))
    download(cache, model, emit, stop, revision=revision)


def remove_model(cache, model):
    target = cache_folder(cache, model).resolve()
    root = Path(cache).resolve()
    if target == root or root not in target.parents or target.name != cache_folder(cache, model).name:
        raise ValueError(tr('model_catalog.remove_model.invalid_model_path_deletion_refused'))
    from ownership import Lease
    with Lease(root/'.models.lock', reentrant=False):
        if target.exists():
            shutil.rmtree(target)

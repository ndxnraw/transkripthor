"""Publish immutable TXT/SRT generations with one atomic manifest switch."""
from ndtranskripthor.core.i18n import tr
import json
import uuid
from ndtranskripthor.core.atomic import atomic_text


class ExportCopyError(OSError):
    pass


def latest_pair(folder, suffix):
    exports = folder / 'exporty'
    manifest = json.loads((exports/f'aktualny{suffix}.json').read_text(encoding='utf-8'))
    directory = (exports/manifest['directory']).resolve()
    if directory.parent != exports.resolve() or any(
            not (directory/name).is_file() for name in (f'prepis{suffix}.txt', f'titulky{suffix}.srt')):
        raise ValueError(tr('export_pair.latest_pair.published_export_is_incomplete_retry_export'))
    return directory


def publish_pair(folder, suffix, text, srt, metadata, write=atomic_text):
    exports = folder / 'exporty'
    generation = exports / uuid.uuid4().hex
    generation.mkdir(parents=True)
    txt_name, srt_name = f'prepis{suffix}.txt', f'titulky{suffix}.srt'
    # Unreferenced incomplete generations are never published or selected.
    write(generation/txt_name, text, 'utf-8-sig')
    write(generation/srt_name, srt, 'utf-8-sig')
    manifest = dict(metadata, directory=generation.name, txt=txt_name, srt=srt_name)
    write(exports/f'aktualny{suffix}.json', json.dumps(manifest, ensure_ascii=False), 'utf-8')
    # Historical root paths are compatibility copies, not the atomic pair.
    try:
        write(folder/txt_name, text, 'utf-8-sig')
        write(folder/srt_name, srt, 'utf-8-sig')
    except OSError as exc:
        raise ExportCopyError(tr('export_pair.publish_pair.the_txt_srt_pair_is_published_in_copies_in', p0=generation, p1=exc)) from exc
    return generation

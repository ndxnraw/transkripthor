"""Read-only local storage inventory and an allowlisted diagnostic snapshot."""
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import stat
import tempfile
import time
import zipfile
from ndtranskripthor.queueing.state import STATES
from version import DISPLAY_VERSION

PACKAGES = ('faster-whisper', 'ctranslate2', 'torch', 'transformers', 'huggingface-hub', 'tkinterdnd2')


def measure(folder, stop, *, limit=100000, seconds=15):
    """Logical file bytes, no content reads and no traversal of reparse points.

    Bounds include directory entries, not just files. Inaccessible/changing trees
    and bounded scans are explicitly partial, never a reliable zero.
    """
    size = files = entries = 0
    incomplete = False
    pending = [Path(folder)]
    deadline = time.monotonic() + seconds
    while pending:
        if stop.is_set() or entries >= limit or time.monotonic() >= deadline:
            incomplete = True
            break
        path = pending.pop()
        try:
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                incomplete = True
                continue
            if stat.S_ISDIR(info.st_mode):
                with os.scandir(path) as children:
                    for child in children:
                        if stop.is_set() or entries >= limit or time.monotonic() >= deadline:
                            incomplete = True
                            break
                        entries += 1
                        pending.append(Path(child.path))
            elif stat.S_ISREG(info.st_mode):
                size += info.st_size
                files += 1
        except FileNotFoundError:
            if path == Path(folder) and not entries:
                return dict(bytes=0, files=0, state='missing')
            incomplete = True
        except OSError:
            incomplete = True
    return dict(bytes=size, files=files, state='partial' if incomplete else 'complete')


def inventory(profile, models, output, projects, stop):
    roots = [('profile', Path(profile)), ('models', Path(models)), ('output', Path(output)),
             ('temporary', Path(tempfile.gettempdir())/'nd-transkripthor-pcm')]
    seen = set()
    for folder in projects:
        path = Path(folder).absolute()
        key = os.path.normcase(str(path))
        if key not in seen:
            roots.extend([('project', path), ('project_cache', path/'.pcm-cache')])
            seen.add(key)
    rows = []
    for kind, path in roots:
        if stop.is_set():
            break
        rows.append(dict(kind=kind, path=str(path.absolute()), **measure(path, stop)))
    return rows


def diagnostic_snapshot(rows, states, offline):
    """Never copy caller dictionaries: paths, errors, tokens and text stay out."""
    versions = {}
    for name in PACKAGES:
        try:
            value = importlib.metadata.version(name)
            versions[name] = value if re.fullmatch(r'[0-9][0-9A-Za-z.+_-]{0,63}', value) else 'unknown'
        except importlib.metadata.PackageNotFoundError:
            versions[name] = 'missing'
    kinds = ('profile', 'models', 'output', 'temporary', 'project', 'project_cache')
    storage = []
    for row in rows:
        if row.get('kind') in kinds:
            storage.append(dict(kind=row['kind'], bytes=max(0, int(row['bytes'])), files=max(0, int(row['files'])),
                                state=row['state'] if row['state'] in ('missing','partial','complete') else 'partial'))
    return json.dumps(dict(schema=1, application='ND TranskripThor', channel=DISPLAY_VERSION,
        python=platform.python_version(), platform='Windows' if os.name=='nt' else 'other',
        architecture=platform.architecture()[0], packages=versions, offline=bool(offline),
        queue={state: states.count(state) for state in STATES}, storage=storage), ensure_ascii=False, indent=2)+'\n'


NOTICE = ('Local diagnostic snapshot only. No audio, transcript text, project files, paths, '
          'settings files, logs, device names, hostnames or credentials are included. '
          'Storage sizes are logical bytes, may overlap, and are a point-in-time observation.\n')


def save_bundle(destination, snapshot):
    """Write exactly the previewed UTF-8 snapshot; publish only a finished ZIP."""
    path = Path(destination)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.nd-diagnostic-', suffix='.tmp', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr('diagnostics.json', snapshot.encode('utf-8'))
                bundle.writestr('README.txt', NOTICE.encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

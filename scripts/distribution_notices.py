"""Collect original notices and disclose unresolved provenance; no licence guessing."""
import json
from pathlib import Path
import shutil
import sys
from packaging.utils import canonicalize_name
from verify_environment import pins

ROOT = Path(__file__).resolve().parents[1]


def collect(target, installed, root=ROOT):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    names = set(pins(root/'requirements/runtime.lock')) | set(pins(root/'requirements/speakers.lock'))
    # Include bootloader/build notices; production Qt is in the runtime lock.
    names |= {'pyinstaller', 'setuptools'}
    inventory = []
    for dist in sorted(installed, key=lambda d: d.metadata['Name'].lower()):
        name = canonicalize_name(dist.metadata['Name'])
        if name not in names:
            continue
        copied = []
        for relative in dist.files or []:
            relative = Path(relative)
            if not any(word in relative.name.lower() for word in ('license', 'licence', 'copying', 'notice')):
                continue
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe licence metadata path')
            source = Path(dist.locate_file(relative))
            if source.is_file():
                destination = target/name/relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                copied.append(destination.relative_to(target).as_posix())
        inventory.append(dict(name=name, version=dist.version, notices=copied,
                              status='collected' if copied else 'missing-notice'))
    python_license = Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.is_file():
        shutil.copy2(python_license, target/'PYTHON-LICENSE.txt')
    supplementary = root/'packaging/notices'
    if supplementary.is_dir():
        shutil.copytree(supplementary, target/'supplementary', dirs_exist_ok=True)
        for row in inventory:
            extra = supplementary/(row['name']+'-LICENSE.txt')
            if not row['notices'] and extra.is_file():
                row['notices'] = ['supplementary/'+extra.name]
                row['status'] = 'upstream-notice'
    for source in (Path(sys.base_prefix)/'tcl').rglob('license.terms'):
        destination=target/'Python-Tcl-Tk'/source.relative_to(Path(sys.base_prefix)/'tcl')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
    # Explicitly a superset of the build's runtime lock, not a claim each library
    # is present in the basic binary. Native dependencies need separate review.
    result = dict(schema=1, scope='runtime-lock-superset', libraries=inventory,
                  missing_notices=[d['name'] for d in inventory if not d['notices']],
                  release_ready=False,
                  unresolved=['Confirm exact FFmpeg and native dependency source provenance and redistribution notices before public release.',
                              'Validate application distribution licence and clean Windows acceptance before public release.'])
    (target/'inventory.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result

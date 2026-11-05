"""Compare every bundled application module with the current source."""
import argparse
import marshal
from pathlib import Path
from types import CodeType
from PyInstaller.archive.readers import CArchiveReader


def signature(code):
    if not isinstance(code, CodeType):
        return code
    return (code.co_code, code.co_names, code.co_varnames, code.co_argcount,
            code.co_kwonlyargcount, tuple(signature(item) for item in code.co_consts))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exe', type=Path)
    parser.add_argument('--qml', action='store_true')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / 'src'
    archive = CArchiveReader(str(args.exe))
    embedded = archive.open_embedded_archive('PYZ.pyz')
    checked = 0
    for path in sorted(source.rglob('*.py')):
        if not args.qml and path.is_relative_to(source/'prototype_qml'):
            continue  # Separately packaged experiment, not part of the Tk distribution.
        if args.qml and path == source/'prepis.py':
            continue  # The experiment has its own audited entry point below.
        if path.parent == source and path.stem in ('check_runtime', 'evaluate_mixed', 'stiahnut_model'):
            # Standalone CLI launchers are not frozen dependencies. All package
            # modules (including evaluation and diagnostics) are audited below.
            continue
        relative = path.relative_to(source).with_suffix('')
        module = '.'.join(relative.parts)
        if module.endswith('.__init__'):
            module = module[:-9]
        entry = relative.as_posix() in ('prepis', 'prototype_qml/main')
        frozen = marshal.loads(archive.extract('main' if args.qml else 'prepis')) if entry else embedded.extract(module)
        if signature(frozen) != signature(compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec')):
            raise RuntimeError(f'Frozen code differs: {path.name}')
        checked += 1
    print(f'Frozen code matches {checked} application modules')


if __name__ == '__main__':
    main()

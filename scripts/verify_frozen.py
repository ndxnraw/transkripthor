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
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / 'src'
    archive = CArchiveReader(str(args.exe))
    embedded = archive.open_embedded_archive('PYZ.pyz')
    checked = 0
    for path in sorted(source.glob('*.py')):
        if path.stem in ('check_runtime', 'evaluate_mixed', 'stiahnut_model', 'download_progress'):
            # CLI utilities and the older cache monitor are not EXE dependencies.
            # The monitor's existing regressions stay in the required test suite;
            # application downloads use download_transport/download_worker.
            continue
        frozen = marshal.loads(archive.extract('prepis')) if path.stem == 'prepis' else embedded.extract(path.stem)
        if signature(frozen) != signature(compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec')):
            raise RuntimeError(f'Frozen code differs: {path.name}')
        checked += 1
    print(f'Frozen code matches {checked} application modules')


if __name__ == '__main__':
    main()

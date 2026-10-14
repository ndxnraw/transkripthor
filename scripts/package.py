"""Package an already verified Windows build, without publishing a release."""
import argparse
import hashlib
from importlib.metadata import distributions
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    app, output = args.app.resolve(), args.output.resolve()
    if not (app / 'ND TranskripThor.exe').is_file() or not (app / '_internal').is_dir():
        raise ValueError('Complete onedir build required')
    if output.exists() or output.with_suffix('.sha256').exists():
        raise FileExistsError('Do not overwrite an existing package/checksum')
    for distribution in distributions():
        for relative in distribution.files or []:
            if any(word in relative.name.lower() for word in ('license', 'licence', 'copying')):
                source = Path(distribution.locate_file(relative))
                if source.is_file():
                    target = app / 'LICENCIE' / distribution.metadata['Name'] / relative
                    if '..' in relative.parts or relative.is_absolute():
                        raise ValueError('Unsafe distribution metadata path')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'x', ZIP_DEFLATED, compresslevel=3) as archive:
        for path in sorted(app.rglob('*')):
            if path.is_file() and (path.name == 'ND TranskripThor.exe' or path.relative_to(app).parts[0] in ('_internal', 'LICENCIE')):
                archive.write(path, Path(app.name) / path.relative_to(app))
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('ZIP integrity check failed')
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_suffix('.sha256').write_text(f'{digest}  {output.name}\n', encoding='ascii')
    print('Verified ZIP:', output)


if __name__ == '__main__':
    main()

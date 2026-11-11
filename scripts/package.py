"""Package an already verified Windows build, without publishing a release."""
import argparse
from importlib.metadata import distributions
from pathlib import Path
import shutil
import json
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--release-tag', help='Explicit release tag, for example v1; otherwise package a candidate')
    args = parser.parse_args()
    app, output = args.app.resolve(), args.output.resolve()
    if not (app / 'ND TranskripThor.exe').is_file() or not (app / '_internal').is_dir():
        raise ValueError('Complete onedir build required')
    if output.exists() or output.with_suffix('.sha256').exists():
        raise FileExistsError('Do not overwrite an existing package/checksum')
    from build_receipt import verify
    receipt = verify(app)
    if args.release_tag:
        import re
        import subprocess
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
        from version import VERSION, DISPLAY_VERSION, PRERELEASE
        if PRERELEASE or not re.fullmatch(r'v\d+(?:\.\d+){0,2}',args.release_tag):
            raise ValueError('An explicit stable version and release tag are required')
        root=Path(__file__).resolve().parents[1]
        head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
        dirty=subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True).strip()
        if head!=receipt['commit'] or dirty:
            raise ValueError('Release packaging requires the exact clean committed build')
    output.parent.mkdir(parents=True, exist_ok=True)
    from distribution_notices import collect
    from build_receipt import digest
    with tempfile.TemporaryDirectory(prefix='Thor package ', dir=output.parent) as temporary:
        staging = Path(temporary)
        collect(staging/'LICENCIE', distributions())
        sources = {p.relative_to(app).as_posix(): p for p in app.rglob('*') if p.is_file()
                   and (p.name in ('ND TranskripThor.exe', 'build-manifest.json') or p.relative_to(app).parts[0] == '_internal')}
        sources.update({p.relative_to(staging).as_posix(): p for p in staging.rglob('*') if p.is_file()})
        variant_file=app/'_internal/distribution-variant.txt'
        variant=variant_file.read_text(encoding='ascii').strip() if variant_file.is_file() else 'extended'
        manifest = dict(schema=1, candidate=not bool(args.release_tag), signature='not-verified', variant=variant, commit=receipt['commit'],
                        frontend='qml' if 'build-qt.ps1' in receipt['verification'] else 'tk',
                        files={name:dict(bytes=p.stat().st_size, sha256=digest(p)) for name,p in sorted(sources.items())})
        if args.release_tag: manifest.update(release_tag=args.release_tag,version=VERSION,display_version=DISPLAY_VERSION)
        manifest_path=staging/'distribution-manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
        sources[manifest_path.name]=manifest_path
        pending=staging/'candidate.zip'
        with ZipFile(pending, 'x', ZIP_DEFLATED, compresslevel=3) as archive:
            for name,path in sorted(sources.items()):
                archive.write(path, Path(app.name)/name)
        with ZipFile(pending) as archive:
            if archive.testzip() is not None:
                raise RuntimeError('ZIP integrity check failed')
        checksum=digest(pending)
        # Exclusive creation prevents an intervening package from being overwritten.
        with output.open('xb') as destination, pending.open('rb') as source:
            shutil.copyfileobj(source,destination)
        with output.with_suffix('.sha256').open('x', encoding='ascii') as stream:
            stream.write(f'{checksum}  {output.name}\n')
        print('Uncompressed bytes:', sum(row['bytes'] for row in manifest['files'].values())+manifest_path.stat().st_size)
        print('ZIP bytes:', output.stat().st_size)
    print('Verified ZIP:', output)


if __name__ == '__main__':
    main()

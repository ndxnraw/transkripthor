"""Verify ZIP checksum and every manifested member before optional extracted EXE smoke."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def verify(path):
    path=Path(path)
    expected=path.with_suffix('.sha256').read_text(encoding='ascii').strip()
    with path.open('rb') as stream:
        actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if expected != f'{actual}  {path.name}':
        raise ValueError('ZIP checksum mismatch')
    with ZipFile(path) as archive:
        names=archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError('Duplicate ZIP members')
        for name in names:
            parts=PurePosixPath(name)
            if parts.is_absolute() or '..' in parts.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe ZIP member')
        manifests=[n for n in names if n.endswith('/distribution-manifest.json')]
        if len(manifests)!=1:
            raise ValueError('One distribution manifest required')
        parent=manifests[0].rsplit('/',1)[0]
        manifest=json.loads(archive.read(manifests[0]))
        if manifest['schema'] != 1:
            raise ValueError('Unsupported distribution schema')
        expected_names={parent+'/'+name for name in manifest['files']} | {manifests[0]}
        if set(names)!=expected_names:
            raise ValueError('ZIP file set differs from manifest')
        total=archive.getinfo(manifests[0]).file_size
        for name,row in manifest['files'].items():
            info=archive.getinfo(parent+'/'+name)
            if info.file_size != row['bytes']:
                raise ValueError('File size mismatch: '+name)
            with archive.open(info) as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=row['sha256']:
                    raise ValueError('File checksum mismatch: '+name)
            total+=info.file_size
    return parent, dict(zip_bytes=path.stat().st_size, unpacked_bytes=total,
                       variant=manifest.get('variant'), commit=manifest.get('commit'),frontend=manifest.get('frontend','tk'),
                       release_tag=manifest.get('release_tag'),version=manifest.get('version'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip',type=Path)
    parser.add_argument('--startup',action='store_true')
    args=parser.parse_args()
    parent,report=verify(args.zip)
    if args.startup:
        with tempfile.TemporaryDirectory(prefix='Thor extracted č ') as folder:
            with ZipFile(args.zip) as archive: archive.extractall(folder)
            frontend=report['frontend']
            if frontend not in ('qml','tk'): raise ValueError('Unknown application frontend')
            verifier='verify_qt_exe.py' if frontend=='qml' else 'verify_exe.py'
            subprocess.run([sys.executable,str(Path(__file__).with_name(verifier)),
                            str(Path(folder)/parent/'ND TranskripThor.exe')],check=True,timeout=150)
        report['extracted_startup']='PASS'
    print(json.dumps(report,indent=2))

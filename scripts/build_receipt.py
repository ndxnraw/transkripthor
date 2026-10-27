"""Build provenance and a gate against packaging stale or modified onedir output."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from verify_environment import check_environment

ROOT=Path(__file__).resolve().parents[1]
NAME='build-manifest.json'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def tree(folder, source=False):
    return {p.relative_to(folder).as_posix():digest(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and p.relative_to(folder).as_posix()!=NAME and (not source or ('__pycache__' not in p.parts and p.suffix!='.pyc'))
            and 'LICENCIE' not in p.relative_to(folder).parts}


def inputs(root):
    result={'.python-version':digest(root/'.python-version')}
    for name in ('src','scripts','tests','requirements','packaging'):
        result.update({name+'/'+key:value for key,value in tree(root/name,source=True).items()})
    return result


def write(app,data):
    app.mkdir(parents=True,exist_ok=True)
    temporary=app/(NAME+'.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(app/NAME)


def begin(app,root=ROOT):
    receipt=app/NAME
    if receipt.exists():
        backup=root/'build'/'previous-build-manifests'
        backup.mkdir(parents=True,exist_ok=True)
        shutil.copy2(receipt,backup/(digest(receipt)+'.json'))
    write(app,dict(schema=1,status='pending'))


def create(app,root=ROOT):
    versions=check_environment('build',root=root)
    expected=(root/'.python-version').read_text(encoding='ascii').strip()
    if platform.python_version()!=expected: raise ValueError('Unexpected Python patch version')
    if not (app/'ND TranskripThor.exe').is_file() or not (app/'_internal').is_dir():
        raise ValueError('Complete Windows onedir build required')
    try:
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError): commit=None
    write(app,dict(schema=1,status='verified',python=expected,python_executable_sha256=digest(Path(sys._base_executable)),
        libraries=versions,inputs=inputs(root),files=tree(app),commit=commit,
        verification='scripts/build.ps1: full tests, frozen source comparison and startup passed'))


def verify(app,root=ROOT):
    receipt=json.loads((app/NAME).read_text(encoding='utf-8'))
    if receipt.get('schema')!=1 or receipt.get('status')!='verified': raise ValueError('Build is not verified; run scripts/build.ps1')
    if receipt['python']!=platform.python_version(): raise ValueError('Python differs from verified build')
    if receipt['inputs']!=inputs(root): raise ValueError('Build inputs changed; rebuild before packaging')
    if receipt['files']!=tree(app): raise ValueError('Build output changed; rebuild before packaging')
    if receipt['libraries']!=check_environment('build',root=root): raise ValueError('Build environment changed')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('begin','create','verify'))
    parser.add_argument('app',type=Path)
    args=parser.parse_args()
    globals()[args.action](args.app.resolve())
    print('Build manifest:',args.action,'PASS')

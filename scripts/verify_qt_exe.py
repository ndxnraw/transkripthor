"""Check QML resources and exercise the actual frozen production Qt window."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('exe',type=Path); args=parser.parse_args()
    source=Path(__file__).resolve().parents[1]/'src'
    sys.path.insert(0,str(source))
    from version import DISPLAY_VERSION, WINDOWS_VERSION, PRERELEASE
    from PyInstaller.utils.win32.versioninfo import read_version_info_from_executable
    info=read_version_info_from_executable(str(args.exe))
    numbers=info.ffi
    actual=(numbers.fileVersionMS>>16,numbers.fileVersionMS&65535,numbers.fileVersionLS>>16,numbers.fileVersionLS&65535)
    assert actual==WINDOWS_VERSION,(actual,WINDOWS_VERSION)
    assert bool(numbers.fileFlags&2)==PRERELEASE,'Wrong Windows pre-release flag'
    assert DISPLAY_VERSION in str(info),'Wrong displayed Windows version'
    for path in (source/'ndtranskripthor/presentation/qml').glob('*.qml'):
        relative=path.relative_to(source)
        assert (args.exe.parent/'_internal'/relative).read_bytes()==path.read_bytes(),relative
    for relative in ('assets/transkripthor.png','locales/sk.json','locales/en.json'):
        assert (args.exe.parent/'_internal'/relative).read_bytes()==(source/relative).read_bytes(),relative
    with tempfile.TemporaryDirectory(prefix='Thor Qt frozen č ') as folder:
        root=Path(folder)
        environment=dict(os.environ)
        environment.pop('PYTHONPATH',None); environment.pop('PYTHONHOME',None)
        environment['PATH']=os.pathsep.join((str(Path(os.environ['SystemRoot'])/'System32'),os.environ['SystemRoot']))
        environment['PYTHONNOUSERSITE']='1'
        subprocess.run([str(args.exe.resolve()),'--profile',str(root/'profil č'),'--smoke-output',str(root/'diagnostic')],cwd=root,env=environment,check=True,timeout=120)
        report=json.loads((root/'diagnostic/qml-smoke.json').read_text(encoding='utf-8'))
        assert report['status']=='PASS',report
        print('Frozen production QML: Windows version, project, save, five exports, seek, themes, native ASR imports/spawn, no Tk/warnings: PASS')


if __name__=='__main__': main()

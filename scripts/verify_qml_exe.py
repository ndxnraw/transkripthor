"""Run the actual frozen QML window and persistence services in an isolated profile."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
parser=argparse.ArgumentParser();parser.add_argument('exe',type=Path);args=parser.parse_args()
source=Path(__file__).resolve().parents[1]/'src'
for relative in ('prototype_qml/Main.qml','assets/transkripthor.png'):
    assert (args.exe.parent/'_internal'/relative).read_bytes()==(source/relative).read_bytes(),relative
with tempfile.TemporaryDirectory(prefix='Thor QML frozen č ') as folder:
    root=Path(folder)
    subprocess.run([str(args.exe.resolve()),'--profile',str(root/'profile'),'--smoke-output',str(root/'diagnostic')],check=True,timeout=90)
    report=json.loads((root/'diagnostic/qml-smoke.json').read_text(encoding='utf-8'))
    assert report['status']=='PASS',report
    print('Frozen QML, queue, project copy, edit/save, seek and themes: PASS')

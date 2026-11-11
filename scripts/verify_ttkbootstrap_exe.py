"""Copy the preview to a Unicode path, run with no Python on PATH, inspect report."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('exe', type=Path)
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='Thor ttk EXE medzera č 日本 ') as folder:
    target = Path(folder)/'Aplikácia'
    shutil.copytree(args.exe.resolve().parent, target)
    report = Path(folder)/'smoke.json'
    environment = dict(os.environ)
    environment['PATH'] = os.pathsep.join((str(Path(os.environ['SystemRoot'])/'System32'), os.environ['SystemRoot']))
    environment.pop('PYTHONPATH', None)
    environment.pop('PYTHONHOME', None)
    run = subprocess.run([str(target/args.exe.name), '--smoke-output', str(report)], cwd=folder,
                         env=environment, capture_output=True, text=True, timeout=90)
    if run.returncode:
        raise RuntimeError(f'Preview EXE failed ({run.returncode}): {run.stdout} {run.stderr}')
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['status'] == 'PASS' and len(data['cycles']) == 3, data
    output = args.exe.parent/'ttkbootstrap-smoke.json'
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Frozen preview: Unicode path, themes, tkdnd, 3 root lifecycles, no Python on PATH: PASS')

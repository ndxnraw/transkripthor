"""Model-free frozen startup, Tk/resources and spawned-process smoke test."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exe', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='Thor smoke ') as folder:
        output = Path(folder) / 'overenie s medzerami a diakritikou'
        output.mkdir()
        subprocess.run([str(args.exe.resolve()), '--self-test-startup', str(output)],
                       cwd=folder, check=True, timeout=90)
        report = json.loads((output / 'startup.json').read_text(encoding='utf-8'))
        if report['status'] != 'PASS' or report['worker_pid'] == report['parent_pid']:
            raise RuntimeError('Frozen startup/process diagnostic failed')
        print('Frozen Tk, tkdnd, translations, assets, native imports and spawn: PASS')


if __name__ == '__main__':
    main()

"""Optional real Tiny CPU ASR in the frozen process; inputs must be authorized."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exe', type=Path)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for name in ('first', 'repeat'):
        target = args.output.resolve() / name
        subprocess.run([str(args.exe.resolve()), '--self-test-process', str(args.cache.resolve()),
                        str(args.audio.resolve()), str(target)], check=True, timeout=300)
        report = json.loads((target / 'process-diagnostic.json').read_text(encoding='utf-8'))
        if report['status'] != 'PASS':
            raise RuntimeError(f'ASR diagnostic failed: {name}')
        print(name, report['seconds'], 'seconds', report['segments'], 'segments')


if __name__ == '__main__':
    main()

"""Generate Windows wheel locks from a clean pip --dry-run --ignore-installed report.

The resolver inputs and constraints are reviewed separately. Never use pip freeze
from a shared environment. Reports contain only the declared dependency closure.
"""
import argparse
import json
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
ROOTS = {
    'runtime': ['faster-whisper', 'Pillow', 'sounddevice', 'tkinterdnd2',
                'torch', 'transformers', 'huggingface-hub'],
    'speakers': ['kaldi-native-fbank'],
    'build': ['PyInstaller', 'pyinstaller-hooks-contrib'],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path, nargs='+')
    args = parser.parse_args()
    packages = {}
    for path in args.report:
        report = json.loads(path.read_text(encoding='utf-8'))
        environment = dict(report['environment'], extra='')
        if environment['sys_platform'] != 'win32' or environment['python_version'] != '3.12':
            raise ValueError('Resolve on Windows Python 3.12')
        for entry in report['install']:
            packages[canonicalize_name(entry['metadata']['name'])] = entry
    def closure(roots):
        found = set()
        def visit(name):
            key = canonicalize_name(name)
            if key in found:
                return
            entry = packages[key]
            found.add(key)
            for raw in entry['metadata'].get('requires_dist', []):
                dependency = Requirement(raw)
                if dependency.marker is None or dependency.marker.evaluate(environment):
                    if dependency.extras or dependency.url:
                        raise ValueError(f'Review dependency extras/URL: {dependency.name}')
                    candidate = packages[canonicalize_name(dependency.name)]
                    if candidate['metadata']['version'] not in dependency.specifier:
                        raise ValueError(f'Incompatible dependency: {dependency.name}')
                    visit(dependency.name)
        for name in roots:
            visit(name)
        return found
    runtime = closure(ROOTS['runtime'])
    for group, roots in ROOTS.items():
        keys = closure(roots)
        header = '# Windows x64 / CPython 3.12; exact wheel SHA-256 hashes.\n'
        if group == 'build':
            header += '-r runtime.lock\n-r speakers.lock\n'
            keys -= runtime
        lines = []
        for key in sorted(keys):
            entry = packages[key]
            download = entry['download_info']
            if not download['url'].split('?', 1)[0].endswith('.whl'):
                raise ValueError(f'Only wheels are supported: {key}')
            digest = download['archive_info']['hashes']['sha256']
            lines.append(f"{key}=={entry['metadata']['version']} --hash=sha256:{digest}")
        (ROOT / 'requirements' / f'{group}.lock').write_text(header + '\n'.join(lines) + '\n', encoding='utf-8')
    used = closure(sum(ROOTS.values(), []))
    (ROOT / 'requirements' / 'constraints.txt').write_text(
        '# Reviewed clean dependency closure; preserve these versions when resolving.\n' +
        ''.join(f"{key}=={packages[key]['metadata']['version']}\n" for key in sorted(used)), encoding='utf-8')
    print(f'Locked {len(used)} distributions from resolver reports')


if __name__ == '__main__':
    main()

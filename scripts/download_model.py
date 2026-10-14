"""Download an explicit model/revision using the application's verified transport."""
import argparse
from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def main():
    from model_catalog import download, location, cached_path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', choices=['tiny', 'small', 'medium', 'large-v3',
                                        'kinit/whisper-large-v3-sk', 'Wespeaker/wespeaker-voxceleb-resnet34-LM'])
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--revision', help='Exact 40-character snapshot commit; omit for catalog ref')
    args = parser.parse_args()
    download(args.cache.resolve(), args.model, lambda kind, value: print(kind, value, flush=True),
             threading.Event(), revision=args.revision)
    snapshot = cached_path(args.cache.resolve(), args.model, args.revision)
    if snapshot is None:
        raise RuntimeError('Downloaded snapshot is incomplete')
    print('Verified snapshot:', snapshot.name)
    print('Repository:', location(args.cache, args.model)[1])


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()

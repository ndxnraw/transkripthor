"""Optional real Windows UI/ASR restart check using authorized audio and cache."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time
import tkinter as tk
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]


def main():
    from faster_whisper.audio import decode_audio
    import numpy as np
    from prepis import App
    from project import Project
    from test_studio import destroy_window
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=False)
    audio = decode_audio(str(args.audio.resolve()), sampling_rate=16000)
    source = base / 'repeated-synthetic-test.wav'
    with wave.open(str(source), 'wb') as stream:
        stream.setparams((1, 2, 16000, 0, 'NONE', ''))
        for _ in range(12):
            stream.writeframes((audio * 32767).astype('<i2').tobytes())
            stream.writeframes(b'\0\0' * 32000)
    def window():
        root = tk.Tk()
        root.withdraw()
        app = App(root, base / 'profile')
        app.cache = args.cache.resolve()
        app.update_readiness()
        return root, app
    def wait(root, app, cancel=False):
        deadline = time.monotonic() + 300
        cancelled = False
        while app.busy:
            root.update()
            if time.monotonic() > deadline:
                app.cancel()
                raise TimeoutError('UI ASR diagnostic timed out')
            target = app.items[0].get('project')
            if cancel and target and not cancelled:
                path = Path(target) / 'projekt.sqlite3'
                if path.is_file():
                    # Read committed metadata only; never steal the ASR lease.
                    try:
                        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
                            row = db.execute("SELECT value FROM metadata WHERE key='next_chunk'").fetchone()
                    except sqlite3.OperationalError as exc:
                        if 'no such table: metadata' not in str(exc):
                            raise
                        row = None  # The database file can precede its first schema transaction.
                    if row and json.loads(row[0]) >= 1:
                        app.cancel()
                        cancelled = True
            time.sleep(.005)
        if cancel and not cancelled:
            raise RuntimeError('No checkpoint interruption was exercised')
    root, app = window()
    try:
        app.accept_files([str(source)])
        app.language.set('Čeština + slovenčina')
        app.quality.set('Tiny – rýchly test')
        app.offline.set(True)
        app.output.set(str(base / 'results'))
        app.start()
        wait(root, app, cancel=True)
        if app.items[0]['state'] != 'interrupted':
            raise RuntimeError('Interrupted checkpoint was not preserved')
        target = app.items[0]['project']
        with Project(target) as project:
            initial, before = project.segments(), project.get('next_chunk')
        if not app.save_state():
            raise RuntimeError('Cannot persist diagnostic profile')
    finally:
        destroy_window(root)
    root, app = window()
    try:
        if app.items[0]['state'] != 'interrupted':
            raise RuntimeError('Restart lost interrupted queue state')
        app.language.set('Maďarčina')
        app.quality.set('Small – vyvážený')
        app.listbox.selection_set(0)
        app.context_action()
        wait(root, app)
        if app.items[0]['state'] != 'completed' or app.language.get() != 'Maďarčina' or app.quality.get() != 'Small – vyvážený':
            raise RuntimeError('Resume failed or changed pending-job preferences')
        with Project(target) as project:
            segments = project.segments()
            if segments[:len(initial)] != initial or len(segments) <= len(initial):
                raise RuntimeError('Resume changed/lost/duplicated committed segments')
            if project.get('next_chunk') != len(project.get('plan')):
                raise RuntimeError('Not all planned chunks completed')
            if not all(a['end'] <= b['start'] for a, b in zip(segments, segments[1:])):
                raise RuntimeError('Invalid resumed timeline')
            report = dict(status='PASS', stopped_after_chunks=before,
                          total_chunks=project.get('next_chunk'), segments=len(segments),
                          scope='Real Tiny CPU, native UI restart and checkpoint resume; no accuracy benchmark')
        (base / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
    finally:
        destroy_window(root)


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()

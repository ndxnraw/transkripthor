import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
"""Synthetic text benchmark: real Tk heartbeat during worker save and export."""
import json
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from editor import Editor
from prepis import App
from project import Project
from test_studio import destroy_window


def measure(count):
    with tempfile.TemporaryDirectory(prefix='f10-', dir=None) as directory:
        folder = Path(directory)/'project'
        with Project(folder, create=True) as project:
            project.initialize('benchmark.wav', {}, {}, [], count*2*16000)
            project.commit_chunk(0, [dict(start=i*2, end=i*2+1.5, text=f'Segment {i}. Test text.', words=[])
                                     for i in range(count)], 'en')
        root = tk.Tk()
        try:
            app = App(root, Path(directory)/'profile')
            with patch.object(Editor, 'load_audio'):
                editor = Editor(app, folder, parent=app.editor_page)
            app.workspace_tabs.select(app.editor_page)
            root.update()
            result = []
            for phase in ('baseline', 'delta'):
                editor.tree.selection_set('0')
                editor.select()
                editor.text.insert('end', ' Edit.')
                ticks = [time.perf_counter()]
                active = True
                def heartbeat():
                    ticks.append(time.perf_counter())
                    if active:
                        root.after(10, heartbeat)
                root.after(10, heartbeat)
                start = time.perf_counter()
                assert editor.save()
                dispatch = time.perf_counter()-start
                while editor.io_busy:
                    root.update()
                    if time.perf_counter()-start > 180:
                        raise TimeoutError('Benchmark save timeout')
                    time.sleep(.001)
                active = False
                ticks.append(time.perf_counter())
                assert editor.io_success and not editor.dirty
                gaps = sorted((b-a)*1000 for a,b in zip(ticks,ticks[1:]))
                result.append(dict(segments=count, phase=phase, save_dispatch_ms=round(dispatch*1000,2),
                    total_seconds=round(time.perf_counter()-start,3), heartbeat_count=len(gaps),
                    maximum_gap_ms=round(max(gaps),2), p95_gap_ms=round(gaps[int(.95*(len(gaps)-1))],2)))
                root.update()
            return result
        finally:
            destroy_window(root)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--segments', nargs='+', type=int, default=[10000, 100000])
    args = parser.parse_args()
    results = [result for count in args.segments for result in measure(count)]
    args.output.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))

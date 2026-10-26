"""Isolated model-free Windows startup and frozen multiprocessing diagnostic."""
import json
import multiprocessing
import os
from pathlib import Path
import traceback


def child(connection):
    from i18n import Translator
    import faster_whisper
    import sounddevice
    connection.send(dict(pid=os.getpid(), languages=sorted(Translator().catalogs)))
    connection.close()


def run(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    root = process = None
    report = dict(status='FAIL', parent_pid=os.getpid())
    try:
        from check_runtime import check
        check()
        from file_drop import create_root
        from prepis import App
        root = create_root()
        root.withdraw()
        app = App(root, folder / 'profile')
        root.update()
        root.tk.call('package', 'present', 'tkdnd')
        if len(app.items) != 0:
            raise RuntimeError('Diagnostic profile is not empty')
        import sounddevice
        sounddevice.query_devices()
        import numpy as np
        from playback import tempo_blocks
        samples = np.sin(2*np.pi*440*np.arange(16000)/16000).astype('float32')
        count = sum(len(block) for block in tempo_blocks(samples, 0, len(samples), 1.25))
        if not 11000 < count < 14500:
            raise RuntimeError('Bundled playback tempo filter failed')
        report['playback_tempo'] = 'PASS'
        from export_formats import render, ExportOptions, FORMATS
        from subtitles import SubtitleOptions
        files, _ = render([dict(id=0, start=0, end=1, text='Overenie č 日本', words=[])],
                          ExportOptions(FORMATS), SubtitleOptions(), 1, dict(view='original', revision=None))
        import io, zipfile
        from xml.etree import ElementTree as ET
        with zipfile.ZipFile(io.BytesIO(files['prepis.docx'])) as document:
            ET.fromstring(document.read('word/document.xml'))
        if len(files) != 5 or json.loads(files['prepis.json'])['segments'][0]['text'] != 'Overenie č 日本':
            raise RuntimeError('Bundled export formats failed')
        report['export_formats'] = 'PASS'
        import kaldi_native_fbank
        from i18n import Translator
        if set(Translator().catalogs) != {'en', 'sk'}:
            raise RuntimeError('Bundled translation catalogs are missing')
        context = multiprocessing.get_context('spawn')
        parent, writer = context.Pipe(duplex=False)
        process = context.Process(target=child, args=(writer,))
        process.start()
        writer.close()
        if not parent.poll(45):
            raise TimeoutError('Diagnostic child startup timed out')
        response = parent.recv()
        parent.close()
        process.join(15)
        if process.exitcode != 0 or response['languages'] != ['en', 'sk']:
            raise RuntimeError('Diagnostic child failed')
        report.update(status='PASS', worker_pid=response['pid'])
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if process is not None and process.is_alive():
            process.terminate()
            process.join(5)
        if root is not None:
            root.destroy()
        (folder / 'startup.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report['status'] == 'PASS'

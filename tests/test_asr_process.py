import os
import queue
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from ndtranskripthor.application.asr_process import Channel, supervise, worker
from ndtranskripthor.projects.project import Project


def hanging(connection, config, stop, run, gate):
    gate.wait()
    channel = Channel(connection, run, stop)
    while True: time.sleep(.1)  # Responsive heartbeat, no inference progress.


def stale(connection, config, stop, run, gate):
    gate.wait()
    connection.send(dict(version=1, run='wrong-run', seq=1, kind='finished'))


def abandon_parent(connection, config):
    events = queue.Queue()
    threading.Thread(target=supervise, args=(config, threading.Event(), events, 'abandoned'),
                     kwargs=dict(target=hanging)).start()
    _, (_, _, value) = events.get(timeout=10)
    connection.send(int(value.rsplit('pid=', 1)[1]))
    os._exit(19)  # No Python finally/atexit: Windows must close the process tree.


def fixture(connection, config, stop, run, gate):
    from ndtranskripthor.application.asr_batch import BatchRunner
    from ndtranskripthor.asr.speech_models import GPUError
    from ndtranskripthor.core.i18n import set_language
    set_language('en')
    gate.wait()
    channel = Channel(connection, run, stop)
    calls = [0]
    class Model:
        model = SimpleNamespace(device='cpu')
        def transcribe(self, *args, **kwargs):
            calls[0] += 1
            if config.get('crash') and calls[0] == 2: os._exit(17)
            return iter([SimpleNamespace(start=.1, end=1., text='Saved text', words=[])]), SimpleNamespace(language='sk')
    def load(*args, **kwargs):
        if args[3] == 'cuda': raise GPUError('cublas64_12.dll missing')
        return Model()
    try:
        with (patch('ndtranskripthor.models.model_catalog.ensure_model'), patch('ndtranskripthor.models.model_catalog.cached_path', return_value=Path('revision')),
             patch('ndtranskripthor.asr.speech_models.device', return_value='cuda'), patch('ndtranskripthor.asr.speech_models.load_backend', side_effect=load),
             patch('faster_whisper.vad.get_speech_timestamps', return_value=[dict(start=0,end=96000),dict(start=160000,end=256000)])):
            BatchRunner(config, stop, channel).work(*config['arguments'])
    finally:
        channel.closed.set()
        connection.close()


class ProcessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder/'audio.wav'
        with wave.open(str(self.source), 'wb') as wav:
            wav.setparams((1,2,16000,0,'NONE',''))
            wav.writeframes(b'\0\0'*320000)
        self.item = dict(id='one',source=str(self.source),project='',state='waiting',error='')
        self.config = dict(cache=str(self.folder/'models'), batch_ids=['one'], batch_mode='pending',
            resume_settings=None, items=[self.item], ui_language='en',
            arguments=([str(self.source)], str(self.folder/'results'), 'sk', 'tiny', True, 'cpu'))

    def run_process(self, target=fixture, *, stop_after=None, accept=True, acknowledge=True, **limits):
        events, stop = queue.Queue(), threading.Event()
        records = []
        thread = threading.Thread(target=supervise, args=(self.config, stop, events, 'test-run'),
            kwargs=dict(target=target, stop_seconds=.3, **limits))
        start = time.monotonic(); thread.start()
        try:
            while thread.is_alive() or not events.empty():
                if stop_after is not None and time.monotonic()-start > stop_after: stop.set()
                self.assertLess(time.monotonic()-start, 20,
                                f'ASR events before deadline: {[kind for kind, _ in records]}')
                try: _, (run, kind, value) = events.get(timeout=.05)
                except queue.Empty: continue
                self.assertEqual(run, 'test-run'); records.append((kind,value))
                if kind == 'job' and acknowledge:
                    identifier, changes, ack, result = value
                    self.assertEqual(identifier, 'one')
                    self.item.update(changes); result.append(True); ack.set()
                elif kind == 'cpu_request' and acknowledge:
                    ack, result = value; result.append(accept); ack.set()
        finally:
            # A failed assertion must not strand a non-daemon bridge or child
            # waiting for acknowledgements from a test that has already ended.
            if thread.is_alive(): stop.set()
            thread.join(8)
            self.assertFalse(thread.is_alive(), 'ASR test bridge did not stop')
        self.assertEqual(sum(k=='finished' for k,v in records), 1)
        return records

    def test_deadline_failure_stops_bridge_without_relaxing_limit(self):
        ended = threading.Event()
        def waiting(config, stop, events, run, **limits):
            stop.wait()
            ended.set()
        with patch('test_asr_process.supervise', side_effect=waiting), \
             patch('test_asr_process.time.monotonic', side_effect=[0, 21]):
            with self.assertRaisesRegex(AssertionError, 'not less than 20'):
                self.run_process()
        self.assertTrue(ended.is_set())

    def test_real_process_crash_checkpoint_and_repeat_resume(self):
        self.config['crash'] = True
        records = self.run_process()
        self.assertTrue(any(k=='process_exit' and '17' in v[0] for k,v in records))
        with Project(self.item['project']) as project:
            self.assertEqual(project.get('next_chunk'), 1)
            self.assertEqual(len(project.segments()), 1)
        self.config['crash'] = False
        records = self.run_process()
        self.assertFalse(any(k == 'process_exit' for k, _ in records), records)
        with Project(self.item['project']) as project:
            self.assertTrue(project.get('complete'))
            self.assertEqual([s['start'] for s in project.segments()], [.1,10.1])
        self.run_process()  # A completed project is exported, never duplicated.
        with Project(self.item['project']) as project:
            self.assertEqual(len(project.segments()), 2)

    def test_gpu_confirmation_and_cancel_across_pipe(self):
        args = list(self.config['arguments']); args[-1] = 'cuda'; self.config['arguments'] = args
        records = self.run_process(accept=False)
        self.assertTrue(any(k=='cpu_request' for k,v in records))
        self.assertFalse(any(k=='device' and v=='CPU' for k,v in records))
        records = self.run_process(accept=True)
        self.assertIn(('device','CPU'), records)
        self.assertEqual(self.item['state'], 'completed')

    def test_stop_hung_process_has_bounded_completion(self):
        records = self.run_process(hanging, stop_after=.5)
        self.assertTrue(any(k=='process_exit' for k,v in records))

    def test_progress_watchdog_ignores_heartbeats(self):
        records = self.run_process(hanging, progress_seconds=1.5)
        self.assertTrue(any(k=='status' and 'not responding' in v for k,v in records))

    def test_missing_ui_ack_has_deadline(self):
        records = self.run_process(acknowledge=False, ack_seconds=.2)
        self.assertTrue(any(k=='process_exit' and 'confirm' in v[0] for k,v in records))

    def test_stale_run_rejected(self):
        records = self.run_process(stale)
        self.assertTrue(any(k=='process_exit' and 'protocol' in v[0] for k,v in records))

    def test_full_ui_queue_has_independent_completion(self):
        events, stop, outcome = queue.Queue(maxsize=1), threading.Event(), {}
        events.put('occupied')
        thread = threading.Thread(target=supervise, args=(self.config, stop, events, 'full'),
            kwargs=dict(target=hanging, outcome=outcome, stop_seconds=.2))
        thread.start(); thread.join(8)
        self.assertFalse(thread.is_alive())
        self.assertTrue(outcome['done'])
        self.assertIn('Full', outcome['reason'])

    @unittest.skipUnless(os.name == 'nt', 'Windows Job Object ownership')
    def test_parent_crash_terminates_owned_asr_process(self):
        import ctypes
        import multiprocessing
        from ctypes import wintypes
        context = multiprocessing.get_context('spawn')
        receiver, sender = context.Pipe(duplex=False)
        host = context.Process(target=abandon_parent, args=(sender, self.config))
        try:
            host.start(); sender.close()
            self.assertTrue(receiver.poll(15))
            pid = receiver.recv()
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.OpenProcess(0x100000, False, pid)
            host.join(5)
            self.assertEqual(host.exitcode, 19)
            if handle:
                try: self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
                finally: kernel.CloseHandle(handle)
        finally:
            if host.is_alive(): host.terminate(); host.join(2)
            receiver.close(); sender.close()

    def test_window_close_stops_hung_process_and_ignores_stale_ui_message(self):
        import tkinter as tk
        from ndtranskripthor.presentation.prepis import App
        from test_studio import destroy_window
        root = tk.Tk()
        def cleanup():
            try: destroy_window(root)
            except tk.TclError: pass
        self.addCleanup(cleanup)
        app = App(root, self.folder/'profile')
        app.accept_files([str(self.source)])
        app.ui_language.set('sk')  # Takes effect after restart, including worker messages.
        def launch(config, stop, events, run, **kwargs):
            supervise(config, stop, events, run, target=hanging, stop_seconds=.3, **kwargs)
        with patch('ndtranskripthor.application.asr_process.supervise', side_effect=launch):
            app.start()
            self.assertTrue(app.busy)
            self.assertEqual(app.asr_config['ui_language'], 'en')
            ack, answer = threading.Event(), []
            app.events.put(('asr', ('stale', 'job', (app.items[0]['id'], {'state':'completed'}, ack, answer))))
            app.poll()
            self.assertFalse(ack.is_set())
            self.assertEqual(app.items[0]['state'], 'waiting')
            app.close()
            deadline = time.monotonic()+10
            while True:
                try:
                    if not root.winfo_exists(): break
                    root.update()
                except tk.TclError:
                    break
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            app.asr_thread.join(2)
            self.assertFalse(app.asr_thread.is_alive())


if __name__ == '__main__':
    unittest.main()

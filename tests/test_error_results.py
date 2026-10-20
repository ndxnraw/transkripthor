"""F20/F21: real local audio decoding/VAD; ASR exceptions are simulated."""
import errno
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock, patch
from app_errors import CATEGORIES, ProjectConflict, CategorizedError, classify, explanation
from jobs import job_settings, transcribe_job
from project import Project
from speech_models import GPUError
from state import StateStore, queue_item
from i18n import Translator
import test_studio


class ErrorResultsTest(unittest.TestCase):
    def test_categories_actions_and_nested_causes(self):
        examples = [
            (FileNotFoundError('missing'), 'input'),
            (OSError(errno.ENOSPC, 'full'), 'disk'),
            (PermissionError('locked'), 'permission'),
            (MemoryError('allocation'), 'memory'),
            (GPUError('cublas64_12.dll'), 'gpu'),
            (CategorizedError('model', 'revision missing'), 'model'),
            (ConnectionError('connection failed'), 'network'),
            (ProjectConflict('changed source'), 'conflict'),
            (RuntimeError('unexpected'), 'unknown')]
        self.assertEqual({category for _, category in examples}, set(CATEGORIES))
        for error, expected in examples:
            with self.subTest(expected=expected):
                wrapper = RuntimeError('outer')
                wrapper.__cause__ = error
                issue = classify(wrapper)
                self.assertEqual(issue['category'], expected)
                self.assertIn(type(error).__name__, issue['details'])
                self.assertNotIn('outer', explanation(issue))
                for locale in ('en', 'sk'):
                    tr = Translator(locale)
                    self.assertFalse(tr('error.'+expected).startswith('['))
                    self.assertFalse(tr('error.action.'+expected).startswith('['))
        self.assertEqual(classify(FileNotFoundError('weights'), 'model')['category'], 'model')

    def test_credentials_are_not_in_diagnostics(self):
        issue = classify(RuntimeError('https://server/file?token=private hf_abc123 password=private'))
        self.assertNotIn('private', issue['details'])
        self.assertNotIn('hf_abc123', issue['details'])

    def test_silence_real_decode_vad_persists_empty_result_and_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder)/'tiché audio.wav', Path(folder)/'project'
            with wave.open(str(source), 'wb') as stream:
                stream.setparams((1, 2, 16000, 0, 'NONE', ''))
                stream.writeframes(b'\0\0' * 32000)
            model = Mock()
            events = []
            args = (model, source, target, job_settings('tiny', 'sk'), threading.Event(),
                    lambda kind, value: events.append((kind, value)))
            self.assertTrue(transcribe_job(*args))
            model.transcribe.assert_not_called()
            result = dict(outcome='no_speech', segment_count=0)
            self.assertIn(('result', result), events)
            with Project(target) as project:
                self.assertEqual(project.get('result'), result)
                self.assertEqual(project.segments(), [])
                self.assertIn('No speech found', project.editor_problem())
            self.assertTrue(transcribe_job(*args, resume=True))
            self.assertEqual(sum(kind == 'result' for kind, _ in events), 2)
            self.assertEqual((target/'prepis.txt').read_text(encoding='utf-8-sig').strip(), '')
            self.assertEqual((target/'titulky.srt').read_text(encoding='utf-8-sig').strip(), '')

    def test_corrupted_recording_is_input_error_not_no_speech(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder)/'broken.wav', Path(folder)/'project'
            source.write_bytes(b'not an audio file')
            events = []
            with self.assertRaises(Exception) as raised:
                transcribe_job(Mock(), source, target, job_settings('tiny', 'sk'),
                               threading.Event(), lambda *event: events.append(event))
            self.assertEqual(classify(raised.exception, 'input')['category'], 'input')
            self.assertFalse(any(kind == 'result' for kind, _ in events))
            with Project(target) as project:
                self.assertFalse(project.get('complete', False))

    def test_queue_roundtrip_preserves_category_and_no_speech(self):
        with tempfile.TemporaryDirectory() as folder:
            store = StateStore(folder)
            item = queue_item(Path(folder)/'voice.wav')
            item.update(state='completed', outcome='no_speech', segment_count=0,
                        error_category='disk', error='technical evidence')
            store.save_queue([item])
            restored = store.queue()[0]
            for key in ('outcome', 'segment_count', 'error_category', 'error'):
                self.assertEqual(restored[key], item[key])


class ErrorUiTest(unittest.TestCase):
    setUp = test_studio.StudioTest.setUp
    tearDown = test_studio.StudioTest.tearDown

    def test_no_speech_queue_and_separate_error_details(self):
        item = queue_item(self.folder/'silent.wav')
        item.update(state='completed', outcome='no_speech', segment_count=0)
        self.app.items = [item]
        self.app.refresh_queue()
        self.app.listbox.selection_set(0)
        self.app.update_selection()
        self.assertIn('No speech found', str(self.app.listbox.item(item['id'], 'values')))
        self.assertIn('No speech found', self.app.selection_info.get())
        item.update(state='failed', outcome='', error_category='permission', error='fixture WinError 32')
        self.app.refresh_queue()
        self.app.listbox.selection_set(0)
        self.app.update_selection()
        self.assertNotIn('WinError', self.app.selection_info.get())
        with patch('prepis.show_error') as dialog:
            self.app.show_item_info()
            self.assertEqual(dialog.call_args.args[2], dict(category='permission', details='fixture WinError 32'))

    def test_technical_details_are_collapsed_and_read_only(self):
        from app_errors import show_error
        from tkinter import Toplevel, Text
        show_error(self.root, 'Fixture', classify(PermissionError('fixture details')))
        window = next(w for w in self.root.winfo_children() if isinstance(w, Toplevel))
        body = next(w for w in window.winfo_children() if any(isinstance(c, Text) for c in w.winfo_children()))
        self.assertEqual(body.winfo_manager(), '')
        button = next(w for w in window.winfo_children() if 'text' in w.keys() and w['text'] == 'Technical details')
        button.invoke()
        self.assertEqual(body.winfo_manager(), 'pack')
        text = next(w for w in body.winfo_children() if isinstance(w, Text))
        self.assertEqual(str(text['state']), 'disabled')
        self.assertIn('fixture details', text.get('1.0', 'end'))
        window.destroy()

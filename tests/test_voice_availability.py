"""F18: preflight uses local fixtures; UI checks do not measure voice accuracy."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ndtranskripthor.asr import speakers
from ndtranskripthor.models.model_catalog import cache_folder, SPEAKER_MODEL, SPEAKER_REVISION
import test_editor_speakers
from test_io_support import save_editor
from ndtranskripthor.projects.project import Project


class AvailabilityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)
        self.folder = cache_folder(self.cache, SPEAKER_MODEL)/'snapshots'/SPEAKER_REVISION
        self.folder.mkdir(parents=True)
        self.weight = self.folder/'voxceleb_resnet34_LM.onnx'
        self.weight.write_bytes(b'fixture, not real ONNX')
        self.modules = {'numpy': SimpleNamespace(stack=object()),
            'onnxruntime': SimpleNamespace(InferenceSession=object(), SessionOptions=object(),
                get_available_providers=lambda: ['CPUExecutionProvider']),
            'kaldi_native_fbank': SimpleNamespace(FbankOptions=object(), OnlineFbank=object())}

    def test_missing_incomplete_model_does_not_import_optional_runtime(self):
        self.weight.write_bytes(b'')
        with patch('ndtranskripthor.asr.speakers.importlib.import_module') as load:
            self.assertIsNone(speakers.availability(self.cache)[0])
            load.assert_not_called()

    def test_each_missing_or_broken_dependency_disables_grouping(self):
        for name in self.modules:
            for error in (ModuleNotFoundError(name), OSError('Missing native DLL')):
                with self.subTest(name=name, error=error):
                    def load(module):
                        if module == name: raise error
                        return self.modules[module]
                    with patch('ndtranskripthor.asr.speakers.importlib.import_module', side_effect=load):
                        path, reason, detail = speakers.availability(self.cache)
                    self.assertIsNone(path)
                    self.assertIn(name, reason)
                    self.assertIn('scripts/setup.ps1 -Speakers', reason)
                    self.assertIn(str(error), detail)

    def test_ready_without_loading_weights_and_missing_cpu_provider(self):
        with patch('ndtranskripthor.asr.speakers.importlib.import_module', side_effect=self.modules.__getitem__):
            self.assertEqual(speakers.availability(self.cache)[0], self.folder)
            self.modules['onnxruntime'].get_available_providers = lambda: []
            self.assertIn('CPUExecutionProvider', speakers.availability(self.cache)[2])


class VoiceControlsTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp
    select = test_editor_speakers.SpeakerEditingTest.select

    def check(self, result):
        with patch('ndtranskripthor.asr.speakers.availability', return_value=result):
            self.editor.refresh_voice_availability()
            deadline = time.monotonic()+3
            while self.editor.voice_check is not None:
                self.assertLess(time.monotonic(), deadline)
                self.editor.poll()
                time.sleep(.01)

    def test_disabled_until_preflight_and_recheck_after_cache_change(self):
        self.assertTrue(self.editor.speaker_button.instate(['disabled']))
        self.check((None, 'Missing kaldi-native-fbank', 'Missing DLL'))
        self.assertTrue(self.editor.speaker_button.instate(['disabled']))
        self.assertIn('Missing DLL', self.editor.voice_status.get())
        self.check((self.folder, 'Ready', ''))
        self.assertFalse(self.editor.speaker_button.instate(['disabled']))
        with patch('ndtranskripthor.asr.speakers.availability', return_value=(None, 'Model removed', '')), \
             patch('ndtranskripthor.presentation.editor.messagebox.askyesno') as confirm:
            self.editor.diarize()
            confirm.assert_not_called()
        self.assertFalse(self.editor.speaker_busy)
        self.assertTrue(self.editor.speaker_button.instate(['disabled']))

    def test_preflight_is_off_ui_thread_and_does_not_dirty_project(self):
        ui_thread = threading.get_ident()
        checked = []
        def check(cache):
            checked.append(threading.get_ident())
            return None, 'Missing model', ''
        with patch('ndtranskripthor.asr.speakers.availability', side_effect=check):
            self.editor.refresh_voice_availability()
            deadline = time.monotonic()+3
            while self.editor.voice_check is not None:
                self.assertLess(time.monotonic(), deadline)
                self.editor.poll(); time.sleep(.01)
        self.assertNotEqual(checked, [ui_thread])
        self.assertEqual(len(checked), 1)
        self.assertFalse(self.editor.dirty)

    def test_manual_choices_clear_undo_save_and_reopen_without_model(self):
        self.select(0)
        self.editor.speaker.set('Ručný hlas')
        self.select(1)
        self.editor.refresh_speaker_choices()
        self.assertIn('Ručný hlas', self.editor.speaker_entry['values'])
        self.editor.speaker.set('Ručný hlas')
        self.editor.capture()
        self.editor.speaker.set('')
        self.editor.capture()
        self.editor.undo()
        self.assertEqual(self.editor.speaker.get(), 'Ručný hlas')
        self.editor.redo()
        self.assertEqual(self.editor.speaker.get(), '')
        self.assertTrue(save_editor(self.editor))
        with Project(self.folder) as project:
            self.assertEqual(project.segments()[0]['speaker'], 'Ručný hlas')
            self.assertEqual(project.segments()[1]['speaker'], '')

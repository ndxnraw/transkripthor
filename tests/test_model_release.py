import threading
import time
import unittest
from unittest.mock import Mock, patch
import test_editor_speakers
from model_dialog import ModelDialog


class ModelReleaseTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp

    def wait(self, dialog):
        deadline = time.monotonic()+10
        while dialog.busy:
            self.root.update()
            if time.monotonic() > deadline:
                self.fail('Model operation timeout')
            time.sleep(.01)

    def test_release_is_guarded_runs_off_ui_and_keeps_model_files(self):
        with patch('model_dialog.inventory', return_value=[]):
            dialog = ModelDialog(self.app, parent=self.app.models_page)
            self.app.model_dialog = dialog
            self.wait(dialog)
            self.app.models.model = self.app.model = Mock()
            self.app.models.key = ('loaded',)
            self.app.busy = True
            dialog.release_model()
            self.assertIsNotNone(self.app.models.model)
            self.app.busy = False
            threads = []
            close = self.app.models.close
            def release():
                threads.append(threading.get_ident())
                close()
            with patch.object(self.app.models, 'close', side_effect=release), patch('model_dialog.remove_model') as remove:
                dialog.release_model()
                self.wait(dialog)
                remove.assert_not_called()
            self.assertIsNone(self.app.models.model)
            self.assertIsNone(self.app.model)
            self.assertIsNone(self.app.models.key)
            self.assertNotEqual(threads, [threading.get_ident()])
            self.assertIn('released', self.app.device_status.get())

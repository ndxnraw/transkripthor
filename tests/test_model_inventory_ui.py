import time
import unittest
from unittest.mock import patch
import test_editor_speakers
from ndtranskripthor.presentation.model_dialog import ModelDialog
from ndtranskripthor.models.model_catalog import inventory


class InventoryUiTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp

    def wait(self, dialog):
        deadline = time.monotonic()+10
        while dialog.busy:
            self.root.update()
            if time.monotonic() > deadline: self.fail('Inventory timeout')
            time.sleep(.01)

    def test_refresh_preserves_selection_focus_scroll_and_group_state(self):
        dialog = ModelDialog(self.app, parent=self.app.models_page)
        self.app.model_dialog = dialog
        self.wait(dialog)
        self.app.workspace_tabs.select(self.app.models_page)
        dialog.tree.configure(height=2)
        dialog.tree.pack_configure(expand=False)
        self.root.update()
        dialog.tree.selection_set('small')
        dialog.tree.focus('small')
        dialog.tree.item('group:speakers', open=False)
        dialog.tree.yview_moveto(.2)
        before = dialog.tree.yview()
        self.assertGreater(before[0], 0)
        dialog.refresh()
        self.wait(dialog)
        self.assertEqual(dialog.tree.selection(), ('small',))
        self.assertEqual(dialog.tree.focus(), 'small')
        self.assertFalse(dialog.tree.item('group:speakers', 'open'))
        self.assertEqual(dialog.tree.yview(), before)
        with patch.object(dialog, 'refresh') as refresh:
            self.app.manage_models()
            refresh.assert_called_once()

    def test_failure_refreshes_inventory_and_keeps_error_visible(self):
        dialog = ModelDialog(self.app, parent=self.app.models_page)
        self.app.model_dialog = dialog
        self.wait(dialog)
        with patch('ndtranskripthor.presentation.model_dialog.inventory', wraps=inventory) as read, patch('ndtranskripthor.presentation.model_dialog.show_error') as details:
            dialog.run(lambda: (_ for _ in ()).throw(ValueError('specific failure')))
            self.wait(dialog)
            read.assert_called_once_with(self.app.cache)
        self.assertIn('model', dialog.status.get())
        self.assertNotIn('specific failure', dialog.status.get())
        self.assertEqual(details.call_args.args[2]['category'], 'model')
        self.assertIn('specific failure', details.call_args.args[2]['details'])
        self.assertTrue(dialog.tree.exists('tiny'))

    def test_stale_cache_result_is_discarded_and_refresh_is_deferred(self):
        dialog = ModelDialog(self.app, parent=self.app.models_page)
        self.app.model_dialog = dialog
        self.wait(dialog)
        self.app.busy = True
        dialog.refresh()
        self.assertTrue(dialog.refresh_pending)
        dialog.events.put(('rows', (self.app.cache/'old', [])))
        dialog.poll()
        self.assertTrue(dialog.tree.exists('tiny'))
        self.app.busy = False
        dialog.poll()
        self.wait(dialog)
        self.assertFalse(dialog.refresh_pending)

    def test_tab_return_during_voice_work_refreshes_when_it_finishes(self):
        dialog = ModelDialog(self.app, parent=self.app.models_page)
        self.app.model_dialog = dialog
        self.wait(dialog)
        self.app.editors.append(self.editor)
        self.editor.speaker_busy = True
        self.app.manage_models()
        self.assertTrue(dialog.refresh_pending)
        self.editor.speaker_busy = False
        with patch('ndtranskripthor.presentation.model_dialog.inventory', wraps=inventory) as read:
            dialog.poll()
            self.wait(dialog)
            read.assert_called_once_with(self.app.cache)

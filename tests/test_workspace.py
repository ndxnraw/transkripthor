"""Main workspace action hierarchy and truthful worker-state presentation."""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest

from ndtranskripthor.presentation.prepis import App
from ndtranskripthor.presentation.ui import apply_theme
from test_studio import destroy_window


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = tk.Tk()
        self.addCleanup(destroy_window, self.root)
        # Tk's display scaling can survive an earlier interpreter on Windows.
        # This action/theme fixture uses 100%; DPI matrices set their own scale.
        self.root.tk.call('tk', 'scaling', 96 / 72)
        self.app = App(self.root, Path(self.temp.name)/'profile')

    def add_audio(self):
        audio = Path(self.temp.name)/'Nahrávka s medzerami 日本.wav'
        audio.write_bytes(b'UI fixture, not ASR audio')
        self.app.accept_files([str(audio)])
        self.app.listbox.selection_set(0)
        self.app.update_selection()
        return audio

    def test_primary_action_requires_pending_work_retry_remains_separate(self):
        app = self.app
        self.assertEqual(str(app.start_button['state']), 'disabled')
        self.add_audio()
        self.assertEqual(str(app.start_button['state']), 'normal')
        app.output.set('   ')
        self.assertEqual(str(app.start_button['state']), 'disabled')
        app.output.set(self.temp.name)
        self.assertEqual(str(app.start_button['state']), 'normal')
        app.items[0]['state'] = 'failed'
        app.refresh_queue()
        self.assertEqual(str(app.start_button['state']), 'disabled')
        self.assertEqual(str(app.context_button['state']), 'normal')
        self.assertEqual(app.context_button['text'], 'Try again')
        app.busy = True
        app.update_selection()
        self.assertEqual(str(app.context_button['state']), 'disabled')

    def test_remove_only_removes_queue_entry_and_never_source(self):
        audio = self.add_audio()
        self.assertEqual(self.app.remove['text'], 'Remove from queue')
        self.app.remove.invoke()
        self.assertTrue(audio.is_file())
        self.assertEqual(self.app.items, [])
        self.assertEqual(str(self.app.start_button['state']), 'disabled')

    def test_phase_badge_does_not_turn_failure_into_success(self):
        app = self.app
        self.assertEqual(app.workspace_state.get(), 'Ready')
        for phase, label in (('loading', 'Loading model'), ('downloading', 'Downloading model'),
                             ('transcribing', 'Transcribing'), ('saving', 'Saving/exporting'),
                             ('stopping', 'Stopping')):
            app.set_phase(phase)
            self.assertEqual(app.workspace_state.get(), label)
        app.events.put(('finished', None))
        app.poll()
        self.assertEqual(app.workspace_state.get(), 'Batch ended')
        self.assertNotIn('success', app.workspace_state.get().lower())

    def test_theme_keeps_card_surfaces_queue_selection_and_action_order(self):
        self.add_audio()
        app = self.app
        app.set_phase('loading')
        selected = app.listbox.selection()
        for mode in ('light', 'dark', 'light'):
            apply_theme(app, mode)
            self.root.update()
            self.assertEqual(app.listbox.selection(), selected)
            self.assertEqual(app.status_view.text['background'], app.theme_manager.palette['card'])
            self.assertEqual(app.readiness_label.text['background'], app.theme_manager.palette['card'])
            for widget in (app.listbox, app.start_button, app.stop_button, app.context_button):
                self.assertTrue(widget.winfo_ismapped(),
                                (str(widget), widget.winfo_geometry(), self.root.winfo_geometry()))
            self.assertLess(app.listbox.winfo_rooty(), app.processing_panel.winfo_rooty())
            self.assertLess(app.processing_panel.winfo_rooty(), app.run_panel.winfo_rooty())
            self.assertEqual(app.start_button['style'], 'Accent.TButton')
            file_center = app.progress.winfo_rooty() + app.progress.winfo_height()/2
            batch_center = app.batch_progress.winfo_rooty() + app.batch_progress.winfo_height()/2
            self.assertLessEqual(abs(file_center - batch_center), 1)

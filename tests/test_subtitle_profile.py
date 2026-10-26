from test_io_support import save_editor, export_editor, wait_io
"""F07: project-local subtitle profiles, including profile-only edits."""
from dataclasses import asdict
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from editor import Editor
from prepis import App
from project import Project
from subtitles import SubtitleOptions
from test_studio import destroy_window


class SubtitleProfileTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)/'project'
        self.create(self.folder)
        self.root = tk.Tk()
        self.addCleanup(destroy_window, self.root)
        self.app = App(self.root, Path(self.temp.name)/'state')
        loader = patch.object(Editor, 'load_audio')
        loader.start()
        self.addCleanup(loader.stop)

    def create(self, folder):
        with Project(folder, create=True) as project:
            project.initialize('audio.wav', {}, {}, [], 160000)
            project.commit_chunk(0, [dict(start=0, end=5, text='Pôvodný text prepisu.', words=[])], 'sk')

    def open(self):
        return Editor(self.app, self.folder, parent=self.app.editor_page)

    def values(self, editor):
        return [value.get() for value in editor.cue_values]

    def test_profile_only_save_on_close_and_reopen(self):
        e = self.open()
        self.assertFalse(e.dirty)
        self.assertIsNone(e.current)
        for value, replacement in zip(e.cue_values, ('55', '3', '0.5', '9.5')):
            e.dirty = False
            value.set(replacement)
            self.assertTrue(e.dirty)
        with patch('editor.messagebox.askyesnocancel', return_value=True) as ask:
            self.assertFalse(e.close())
            self.assertTrue(e.window.winfo_exists())
            wait_io(e)
            self.assertTrue(e.close())
            ask.assert_called_once()
        reopened = self.open()
        self.assertEqual(self.values(reopened), ['55', '3', '0.5', '9.5'])
        self.assertFalse(reopened.dirty)
        with Project(self.folder) as project:
            self.assertEqual(project.get('editor_export')['state'], 'pending')
        self.assertTrue(export_editor(reopened))
        with Project(self.folder) as project:
            expected = asdict(SubtitleOptions(55, 3, .5, 9.5))
            self.assertEqual(project.get('subtitle_options'), expected)
            self.assertEqual(project.get('editor_export')['options'], expected)
            self.assertEqual(project.get('editor_export')['state'], 'complete')
            self.assertEqual(project.segments()[0]['text'], project.segments('original')[0]['text'])
        # Another project does not inherit this profile from the application.
        other = Path(self.temp.name)/'other'
        self.create(other)
        with Project(other) as project:
            self.assertEqual(project.subtitle_options(), SubtitleOptions())

    def test_cancel_discard_and_invalid_profile(self):
        e = self.open()
        e.cue_values[0].set('')
        with patch('editor.messagebox.askyesnocancel', return_value=None):
            self.assertFalse(e.close())
        self.assertTrue(e.window.winfo_exists())
        with patch('editor.messagebox.askyesnocancel', return_value=True), patch('editor.messagebox.showerror') as error:
            self.assertFalse(e.close())
            error.assert_called_once()
        self.assertTrue(e.dirty)
        with Project(self.folder) as project:
            self.assertEqual(project.subtitle_options(), SubtitleOptions())
        with patch('editor.messagebox.askyesnocancel', return_value=False):
            self.assertTrue(e.close())
        reopened = self.open()
        self.assertEqual(float(reopened.cue_values[0].get()), 42)
        self.assertFalse(reopened.dirty)

    def test_legacy_export_profile_is_restored_without_write_on_open(self):
        expected = SubtitleOptions(60, 4, 2, 10)
        with Project(self.folder) as project:
            project.edit(project.segments(), expected)
            with project.db:
                project.db.execute("DELETE FROM metadata WHERE key='subtitle_options'")
        e = self.open()
        self.assertEqual([float(v) for v in self.values(e)], [60, 4, 2, 10])
        self.assertFalse(e.dirty)
        with Project(self.folder) as project:
            self.assertIsNone(project.get('subtitle_options'))
            # Non-UI callers omitting export_options preserve the project profile.
            project.edit(project.segments())
            self.assertEqual(project.get('subtitle_options'), asdict(expected))

    def test_old_project_without_any_profile_uses_defaults(self):
        with Project(self.folder) as project:
            with project.db:
                project.db.execute("DELETE FROM metadata WHERE key='subtitle_options'")
        e = self.open()
        self.assertEqual([float(v) for v in self.values(e)], [42, 2, 1, 7])
        self.assertFalse(e.dirty)

    def test_export_failure_keeps_saved_profile(self):
        e = self.open()
        e.cue_values[0].set('55')
        with patch.object(Project, 'retry_export', side_effect=PermissionError('locked')), patch('editor.messagebox.showerror'):
            self.assertTrue(save_editor(e))
        self.assertFalse(e.dirty)
        with patch('editor.messagebox.askyesnocancel') as ask:
            self.assertTrue(e.close())
            ask.assert_not_called()
        reopened = self.open()
        self.assertEqual(reopened.cue_values[0].get(), '55')
        with Project(self.folder) as project:
            self.assertEqual(project.get('editor_export')['state'], 'pending')
            project.retry_export()
            self.assertEqual(project.subtitle_options().characters, 55)

    def test_failed_transaction_does_not_change_profile(self):
        with Project(self.folder) as project:
            rows = project.segments()
            rows.append(dict(rows[0], id=999))
            with self.assertRaises(ValueError):
                project.edit(rows, SubtitleOptions(55, 3, 2, 8))
            self.assertEqual(project.subtitle_options(), SubtitleOptions())
            self.assertIsNone(project.get('editor_export'))


if __name__ == '__main__':
    unittest.main()

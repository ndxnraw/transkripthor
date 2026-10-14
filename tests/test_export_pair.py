from test_io_support import save_editor, export_editor
import errno
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from editor import Editor
from prepis import App
from project import Project
from state import atomic_text
from test_studio import destroy_window


class ExportPairTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)/'project'
        with Project(self.folder, create=True) as project:
            project.initialize('audio.wav', {}, {}, [], 16000)
            project.commit_chunk(0, [dict(start=0, end=1, text='Originál.', words=[], speaker='')], 'sk')
            project.finish()
            project.export(view='original')
            project.edit(project.segments())
            project.retry_export()
        self.pointer = self.folder/'exporty'/'aktualny.opravene.json'

    def test_failures_keep_previous_pair_and_retry_saved_revision(self):
        previous = self.pointer.read_bytes()
        for failure in (PermissionError(errno.EACCES, 'access denied'), OSError(errno.ENOSPC, 'disk full')):
            with self.subTest(failure=failure):
                with Project(self.folder) as project:
                    rows = project.segments()
                    rows[0]['text'] = str(failure)
                    revision = project.edit(rows)
                    def write(path, *args):
                        if path.suffix == '.srt':
                            raise failure
                        atomic_text(path, *args)
                    with patch('project.atomic_text', side_effect=write):
                        with self.assertRaises(OSError):
                            project.retry_export()
                    self.assertEqual(project.get('editor_export')['state'], 'pending')
                    self.assertEqual(self.pointer.read_bytes(), previous)
                with Project(self.folder) as reopened:
                    reopened.retry_export()
                    self.assertEqual(reopened.get('editor_export')['revision'], revision)
                    self.assertEqual(reopened.get('editor_export')['state'], 'complete')
                manifest = json.loads(self.pointer.read_text())
                pair = self.folder/'exporty'/manifest['directory']
                self.assertTrue((pair/manifest['txt']).is_file())
                self.assertTrue((pair/manifest['srt']).is_file())
                self.assertIn(str(failure), (pair/manifest['txt']).read_text(encoding='utf-8-sig'))
                previous = self.pointer.read_bytes()

    def test_manifest_failure_does_not_publish_incomplete_pair(self):
        previous = self.pointer.read_bytes()
        def write(path, *args):
            if path == self.pointer:
                raise PermissionError('locked manifest')
            atomic_text(path, *args)
        with Project(self.folder) as project:
            with patch('project.atomic_text', side_effect=write):
                with self.assertRaises(PermissionError):
                    project.retry_export()
        self.assertEqual(self.pointer.read_bytes(), previous)

    @unittest.skipUnless(__import__('sys').platform == 'win32', 'Windows file lock')
    def test_real_windows_locked_copy_keeps_published_pair(self):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                      wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.CreateFileW(str(self.folder/'titulky.opravene.srt'), 0x80000000, 0, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try:
            with Project(self.folder) as project:
                revision = project.edit(project.segments())
                with self.assertRaisesRegex(OSError, 'The TXT/SRT pair is published'):
                    project.retry_export()
                self.assertEqual(project.get('editor_export')['state'], 'pending')
                self.assertEqual(json.loads(self.pointer.read_text())['revision'], revision)
        finally:
            kernel.CloseHandle(handle)
        with Project(self.folder) as project:
            project.retry_export()
            self.assertEqual(project.get('editor_export')['state'], 'complete')

    @patch.object(Editor, 'load_audio')
    def test_editor_database_success_export_failure_and_retry_without_new_revision(self, _load):
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(destroy_window, root)
        app = App(root, Path(self.temp.name)/'state')
        editor = Editor(app, self.folder, parent=app.editor_page)
        editor.tree.selection_set('0')
        editor.select()
        editor.text.delete('1.0', 'end')
        editor.text.insert('1.0', 'Uložená oprava.')
        with patch.object(Project, 'export', side_effect=PermissionError('access denied')), \
             patch('editor.messagebox.showerror') as error:
            self.assertTrue(save_editor(editor))
            self.assertFalse(editor.dirty)
            self.assertIn('saved', editor.saved_state.get())
            self.assertIn('incomplete', editor.export_state.get())
            self.assertEqual(error.call_args.args[0], 'TXT/SRT export')
        with Project(self.folder) as project:
            revision = project.get('editor_export')['revision']
            self.assertEqual(project.segments()[0]['text'], 'Uložená oprava.')
        reopened = Editor(app, self.folder, parent=app.editor_page)
        self.assertIn('pending', reopened.export_state.get())
        # Retry must neither capture unsaved text nor create another revision.
        editor.text.insert('end', ' Ešte neuložené.')
        self.assertTrue(export_editor(reopened))
        with Project(self.folder) as project:
            self.assertEqual(project.get('editor_export')['revision'], revision)
            self.assertEqual(project.segments()[0]['text'], 'Uložená oprava.')
        with patch('os.startfile', create=True) as launch:
            reopened.open_export()
            location = Path(launch.call_args.args[0])
            self.assertTrue((location/'prepis.opravene.txt').is_file())
            self.assertTrue((location/'titulky.opravene.srt').is_file())
        # A database failure must not claim success or attempt export.
        with patch.object(Project, 'edit', side_effect=OSError('database full')), \
             patch.object(Project, 'retry_export') as export, patch('editor.messagebox.showerror'):
            self.assertFalse(save_editor(editor))
            self.assertTrue(editor.dirty)
            export.assert_not_called()


if __name__ == '__main__':
    unittest.main()

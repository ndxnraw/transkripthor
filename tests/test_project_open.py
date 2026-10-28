"""F22: independent project opening and content-verified audio relocation."""
import tempfile
import threading
import time
import tkinter as tk
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from ndtranskripthor.presentation.editor import Editor
from ndtranskripthor.presentation.prepis import App
from ndtranskripthor.projects.project import Project, fingerprint
from test_io_support import save_editor
from test_studio import destroy_window


class ProjectOpenTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.audio = self.base/'Pôvodná nahrávka.wav'
        with wave.open(str(self.audio), 'wb') as wav:
            wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            wav.writeframes(b'\0\0'*32000)
        self.digest = fingerprint(self.audio)
        self.folder = self.base/'Projekt mimo fronty'
        with Project(self.folder, create=True) as project:
            project.initialize(self.audio, self.digest, {'model': 'tiny'}, [], 32000)
            project.commit_chunk(0, [dict(start=0, end=1, text='Pôvodný text.', words=[])], 'sk')
            project.finish()

    def test_relocate_preserves_identity_timeline_and_original(self):
        moved = self.base/'Presunutý zvuk 日本.wav'
        self.audio.rename(moved)
        with Project(self.folder) as project:
            original = project.segments('original')
            before = {key: project.get(key) for key in ('settings', 'next_chunk', 'samples', 'fingerprint')}
            self.assertEqual(project.relocate_audio(moved), str(moved.resolve()))
        with Project(self.folder) as project:
            self.assertEqual(project.get('source'), str(moved.resolve()))
            self.assertEqual(project.segments('original'), original)
            self.assertEqual({key: project.get(key) for key in before}, before)

    def test_wrong_same_size_missing_fingerprint_and_cancel_leave_path_unchanged(self):
        wrong = self.base/'wrong.wav'
        wrong.write_bytes(b'x'*self.audio.stat().st_size)
        with Project(self.folder) as project:
            source = project.get('source')
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                project.relocate_audio(wrong)
            stop = threading.Event()
            stop.set()
            with self.assertRaises(InterruptedError):
                project.relocate_audio(self.audio, stop)
            with project.db:
                project.put('fingerprint', None)
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                project.relocate_audio(self.audio)
            self.assertEqual(project.get('source'), source)

    def test_open_after_queue_removal_edit_without_audio_save_reopen_and_relink(self):
        root = tk.Tk()
        self.addCleanup(destroy_window, root)
        app = App(root, self.base/'profile')
        app.accept_files([str(self.audio)])
        app.items[0].update(project=str(self.folder), state='completed')
        app.refresh_queue()
        app.listbox.selection_set(0)
        app.remove_files()
        self.assertEqual(app.items, [])
        moved = self.base/'Zvuk na novom mieste.wav'
        self.audio.rename(moved)
        with patch('ndtranskripthor.presentation.editor.show_error'), patch('ndtranskripthor.presentation.prepis.filedialog.askopenfilename', return_value=str(self.folder/'projekt.sqlite3')):
            app.choose_project()
            editor = app.editors[-1]
            self.wait_audio(root, editor)
        self.assertIsNone(editor.player.audio)
        self.assertIn('Audio unavailable', editor.audio_status.get())
        self.assertEqual(app.items, [])
        editor.tree.selection_set('0')
        editor.select()
        editor.text.delete('1.0', 'end')
        editor.text.insert('1.0', 'Opravený text bez zvuku.')
        self.assertTrue(save_editor(editor))
        self.assertTrue(editor.close())
        with patch('ndtranskripthor.presentation.editor.show_error'):
            app.open_project(self.folder)
            editor = app.editors[-1]
            self.wait_audio(root, editor)
        self.assertEqual(editor.segments[0]['text'], 'Opravený text bez zvuku.')
        wrong = self.base/'Nesprávny zvuk.wav'
        wrong.write_bytes(b'x'*moved.stat().st_size)
        with patch('ndtranskripthor.presentation.editor.show_error') as error, patch('ndtranskripthor.presentation.editor.filedialog.askopenfilename', return_value=str(wrong)):
            editor.locate_audio()
            self.wait_audio(root, editor)
            error.assert_called_once()
        with Project(self.folder) as project:
            self.assertEqual(project.get('source'), str(self.audio.resolve()))
        self.assertIsNone(editor.player.audio)
        with patch('ndtranskripthor.presentation.editor.filedialog.askopenfilename', return_value=str(moved)):
            editor.locate_audio()
            self.wait_audio(root, editor)
        self.assertIsNotNone(editor.player.audio)
        self.assertFalse(editor.dirty)
        self.assertTrue(editor.close())
        with Project(self.folder) as project:
            self.assertEqual(project.get('source'), str(moved.resolve()))
            self.assertEqual(project.segments('original')[0]['text'], 'Pôvodný text.')

    @staticmethod
    def wait_audio(root, editor):
        deadline = time.monotonic()+20
        while editor.audio_busy:
            root.update()
            if time.monotonic() > deadline:
                raise AssertionError('Audio worker timeout')
            time.sleep(.01)

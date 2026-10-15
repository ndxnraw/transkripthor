from test_io_support import save_editor, export_editor
"""F01: real Tk editor and worker scheduling, simulated voice assignments."""
import tempfile
import threading
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from editor import Editor
from jobs import job_settings
from prepis import App
from project import Project
from test_studio import destroy_window


class SpeakerEditingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / 'project'
        with Project(self.folder, create=True) as project:
            project.initialize(self.folder/'audio.wav', {}, job_settings('small', 'sk'), [], 1600000)
            project.commit_chunk(0, [dict(start=i*2, end=i*2+1, text=f'Text {i}.',
                speaker='Pôvodný', language='sk', words=[]) for i in range(45)], 'sk')
            # Persistent IDs deliberately differ from UI indices.
            project.db.execute('UPDATE segments SET id=id+100')
            project.db.commit()
        self.root = tk.Tk()
        if hasattr(self, 'tk_scaling'):
            self.root.tk.call('tk', 'scaling', self.tk_scaling)
        self.root.geometry('1100x800')
        self.addCleanup(destroy_window, self.root)
        self.app = App(self.root, Path(self.temp.name)/'state')
        self.loader = patch.object(Editor, 'load_audio')
        self.loader.start()
        self.addCleanup(self.loader.stop)
        self.editor = Editor(self.app, self.folder, parent=self.app.editor_page)
        self.app.workspace_tabs.select(self.app.editor_page)
        self.editor.player.audio = object()
        self.root.update_idletasks()

    def select(self, index):
        self.editor.tree.selection_set(str(index))
        self.editor.select()

    def start_worker(self, result=None):
        started, release = threading.Event(), threading.Event()
        workers = []
        real_thread = threading.Thread
        def thread_factory(**kwargs):
            worker = real_thread(**kwargs)
            workers.append(worker)
            return worker
        def assign(audio, segments, *args):
            self.snapshot = segments
            started.set()
            if not release.wait(10):
                raise RuntimeError('Test worker timeout')
            return result if result is not None else [f'Hlas {s["id"]}' for s in segments]
        patches = [patch('model_catalog.cached_path', return_value=self.folder),
                   patch('editor.messagebox.askyesno', return_value=True),
                   patch('speakers.assign_speakers', side_effect=assign),
                   patch('editor.threading.Thread', side_effect=thread_factory)]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        def cleanup():
            release.set()
            for worker in workers:
                worker.join(3)
        self.addCleanup(cleanup)
        self.editor.diarize()
        self.assertTrue(started.wait(3))
        self.assertTrue(self.editor.speaker_busy)
        def finish():
            release.set()
            workers[0].join(3)
            self.assertFalse(workers[0].is_alive())
            self.editor.poll()
            self.root.update_idletasks()
            for item in reversed(patches):
                item.stop()
        return finish

    def test_inflight_text_view_and_saved_reopened_project(self):
        for theme in ('light', 'dark'):
            with self.subTest(theme=theme):
                self.app.theme = theme
                self.editor.apply_theme()
                self.select(0)
                finish = self.start_worker()
                with self.assertRaises(TypeError):
                    self.snapshot[0]['start'] = 9
                self.editor.text.delete('1.0', 'end')
                self.editor.text.insert('1.0', 'Prvá oprava počas výpočtu.')
                self.editor.change_page(1)
                self.select(40)
                field = self.editor.text
                text = '\n'.join(f'Rozpísaná oprava {i}.' for i in range(20))
                field.delete('1.0', 'end')
                field.insert('1.0', text)
                field.mark_set('insert', '10.4')
                field.tag_add('sel', '10.1', '10.8')
                self.root.update_idletasks()
                field.yview_moveto(.4)
                self.editor.tree.canvas.yview_moveto(.3)
                self.root.update_idletasks()
                before = (field.index('insert'), field.tag_ranges('sel'), field.yview(),
                          self.editor.tree.canvas.yview(), self.editor.tree.selection(),
                          self.editor.current, self.editor.page, list(self.editor.matches))
                self.assertGreater(field.yview()[0], 0)
                self.assertGreater(self.editor.tree.canvas.yview()[0], 0)
                finish()
                self.assertIs(self.editor.text, field)
                self.assertEqual(before, (field.index('insert'), field.tag_ranges('sel'), field.yview(),
                    self.editor.tree.canvas.yview(), self.editor.tree.selection(),
                    self.editor.current, self.editor.page, self.editor.matches))
                self.assertEqual(self.editor.segments[40]['text'], text)
                self.assertEqual(self.editor.segments[40]['speaker'], 'Hlas 140')
                self.assertEqual(self.editor.speaker.get(), 'Hlas 140')
                self.assertTrue(save_editor(self.editor))
                reopened = Editor(self.app, self.folder, parent=self.app.editor_page)
                self.assertEqual(reopened.segments[0]['text'], 'Prvá oprava počas výpočtu.')
                self.assertEqual(reopened.segments[40]['text'], text)
                self.assertEqual((reopened.segments[40]['start'], reopened.segments[40]['end']), (80, 81))
                self.assertEqual(reopened.segments[40]['speaker'], 'Hlas 140')
                reopened.close()
                exported = (self.folder/'prepis.opravene.txt').read_text(encoding='utf-8-sig')
                self.assertIn(text, exported)
                srt = (self.folder/'titulky.opravene.srt').read_text(encoding='utf-8-sig')
                self.assertIn('00:01:20,000 --> 00:01:21,000', srt)
                self.editor.change_page(-1)

    def test_search_during_worker_keeps_all_edits(self):
        self.select(0)
        finish = self.start_worker()
        self.editor.text.insert('end', ' Oprava pred hľadaním.')
        self.editor.query.set('Text 4')
        self.editor.search()
        self.select(44)
        self.editor.text.insert('end', ' Rozpísané vo filtri.')
        finish()
        self.assertEqual(self.editor.matches, [4, 40, 41, 42, 43, 44])
        self.assertEqual(self.editor.current, 44)
        self.assertTrue(save_editor(self.editor))
        reopened = Editor(self.app, self.folder, parent=self.app.editor_page)
        self.assertEqual(reopened.segments[0]['text'], 'Text 0. Oprava pred hľadaním.')
        self.assertEqual(reopened.segments[44]['text'], 'Text 44. Rozpísané vo filtri.')
        reopened.close()

    def test_manual_assignment_and_change_back_win(self):
        self.select(0)
        finish = self.start_worker()
        self.editor.speaker.set('Daniel')
        self.select(1)
        self.editor.speaker.set('Dočasný')
        self.editor.speaker.set('Pôvodný')
        finish()
        self.assertEqual([s['speaker'] for s in self.editor.segments[:3]],
                         ['Daniel', 'Pôvodný', 'Hlas 102'])
        self.assertTrue(save_editor(self.editor))
        with Project(self.folder) as project:
            self.assertEqual(project.segments()[0]['speaker'], 'Daniel')

    def test_global_rename_wins_over_pending_assignments(self):
        self.select(0)
        finish = self.start_worker()
        with patch('editor.simpledialog.askstring', return_value='Daniel'):
            self.editor.rename_speaker()
        finish()
        self.assertTrue(all(s['speaker'] == 'Daniel' for s in self.editor.segments))

    def test_stale_result_and_changed_timing_are_ignored(self):
        finish = self.start_worker()
        job = self.editor.speaker_job
        self.editor.apply_speakers(object(), {100: 'Zastaralý'})
        self.assertIs(self.editor.speaker_job, job)
        self.editor.segments[0]['end'] = 1.5
        # Reorder without an active editor: results must follow persistent IDs.
        self.editor.segments.reverse()
        finish()
        self.assertEqual(self.editor.segments[0]['speaker'], 'Hlas 144')
        self.assertEqual(self.editor.segments[-1]['speaker'], 'Pôvodný')

    def test_worker_failure_keeps_active_edit(self):
        self.select(0)
        finish = self.start_worker(result=[])
        self.editor.text.insert('end', ' Rozpísané.')
        field = self.editor.text
        finish()
        self.assertFalse(self.editor.speaker_busy)
        self.assertIs(self.editor.text, field)
        self.assertIn('The number of voice results', self.editor.status.get())
        self.assertTrue(save_editor(self.editor))
        with Project(self.folder) as project:
            self.assertEqual(project.segments()[0]['text'], 'Text 0. Rozpísané.')
            self.assertEqual(project.segments()[0]['speaker'], 'Pôvodný')


if __name__ == '__main__':
    unittest.main()

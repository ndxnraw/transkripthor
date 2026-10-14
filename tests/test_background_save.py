"""Real Tk scheduling, worker I/O and isolated transactional queue failures."""
import json
import threading
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
import test_editor_speakers
from project import Project
from state import StateStore, atomic_text, queue_item
from test_io_support import wait_io, save_editor


class BackgroundSaveTest(unittest.TestCase):
    setUp = test_editor_speakers.SpeakerEditingTest.setUp
    select = test_editor_speakers.SpeakerEditingTest.select

    def test_edit_during_save_exports_exact_snapshot_and_keeps_new_edit(self):
        e = self.editor
        self.select(0)
        e.text.insert('end', ' First.')
        entered, release = threading.Event(), threading.Event()
        original = Project.edit
        written = []
        def delayed(project, rows, **kwargs):
            written.extend(rows)
            entered.set()
            if not release.wait(10):
                raise TimeoutError('worker not released')
            return original(project, rows, **kwargs)
        with patch.object(Project, 'edit', delayed):
            self.assertTrue(e.save())
            self.assertTrue(entered.wait(3))
            self.assertFalse(e.close())
            self.assertFalse(e.save())
            self.assertFalse(e.retry_export())
            e.text.insert('end', ' Later.')
            e.capture()
            self.root.update()
            release.set()
            wait_io(e)
        self.assertEqual(len(written), 1)
        self.assertTrue(e.dirty)
        self.assertTrue(e.io_saved)
        with Project(self.folder) as project:
            self.assertEqual(project.segments()[0]['text'], 'Text 0. First.')
            self.assertEqual(project.segments('revision', project.get('editor_export')['revision'])[0]['text'], 'Text 0. First.')
        self.assertNotIn('Later.', (self.folder/'prepis.opravene.txt').read_text(encoding='utf-8-sig'))
        self.assertTrue(save_editor(e))
        self.assertFalse(e.dirty)
        with Project(self.folder) as project:
            revision = project.get('editor_export')['revision']
            data = json.loads(project.db.execute('SELECT data FROM transcript_revisions WHERE id=?', (revision,)).fetchone()[0])
            self.assertEqual(len(data['changes']), 1)
            self.assertEqual(project.segments('revision', revision)[0]['text'], 'Text 0. First. Later.')

    def test_only_changed_segment_is_updated_and_database_failure_can_retry(self):
        e = self.editor
        with Project(self.folder) as project:
            project.db.execute("CREATE TRIGGER unchanged BEFORE UPDATE ON segments WHEN OLD.id != 100 BEGIN SELECT RAISE(ABORT, 'Untouched row rewritten'); END")
            project.db.commit()
        self.select(0)
        e.text.insert('end', ' correction')
        with patch.object(Project, 'edit', side_effect=OSError('disk full')), patch('editor.messagebox.showerror'):
            self.assertFalse(save_editor(e))
        self.assertTrue(e.dirty)
        self.assertIn(100, e.pending_segments)
        self.assertTrue(save_editor(e))
        self.assertFalse(e.dirty)

    def test_queue_mutations_roll_back_together_and_settings_do_not_save_queue(self):
        app = self.app
        paths = [Path(self.temp.name)/name for name in ('a.wav', 'b.wav', 'c.wav')]
        for path in paths:
            path.write_bytes(b'audio')
        self.assertTrue(app.accept_files([str(p) for p in paths[:2]]))
        before = [dict(item) for item in app.items]
        app.listbox.selection_set(0)
        with patch.object(app.store, 'save_queue', side_effect=OSError('disk full')):
            self.assertFalse(app.accept_files([str(paths[2])]))
            self.assertEqual(app.items, before)
            app.remove_files()
            self.assertEqual(app.items, before)
            app.move_item(1)
            self.assertEqual(app.items, before)
            self.assertTrue(app.save_state())
        self.assertEqual(app.store.queue(), before)
        app.move_item(1)
        self.assertEqual(app.store.queue(), list(reversed(before)))

    def test_legacy_queue_migration_keeps_backup(self):
        folder = Path(self.temp.name)/'legacy'
        rows = [queue_item('a.wav')]
        atomic_text(folder/'queue.json', json.dumps(rows))
        before = (folder/'queue.json').read_bytes()
        store = StateStore(folder)
        self.assertEqual(store.queue(), rows)
        self.assertEqual((folder/'queue.json').read_bytes(), before)
        store.save_queue([])
        self.assertEqual(store.queue(), [])
        self.assertEqual((folder/'queue.json').read_bytes(), before)

    def test_queue_partial_transaction_failure_rolls_back(self):
        store = self.app.store
        rows = [queue_item('a.wav'), queue_item('b.wav')]
        store.save_queue(rows)
        with sqlite3.connect(store.folder/'queue.sqlite3') as db:
            db.execute("CREATE TRIGGER fail_second BEFORE INSERT ON queue WHEN NEW.position=1 BEGIN SELECT RAISE(ABORT, 'disk full simulation'); END")
        changed = [dict(row, error='new') for row in rows]
        with self.assertRaises(sqlite3.IntegrityError):
            store.save_queue(changed)
        self.assertEqual(store.queue(), rows)

    def test_undone_edit_does_not_write_unchanged_segment(self):
        e = self.editor
        self.select(0)
        e.text.insert('end', 'temporary')
        e.undo()
        with Project(self.folder) as project:
            project.db.execute("CREATE TRIGGER no_updates BEFORE UPDATE ON segments BEGIN SELECT RAISE(ABORT, 'Unchanged segment'); END")
            project.db.commit()
        self.assertTrue(save_editor(e))
        self.assertFalse(e.dirty)


if __name__ == '__main__':
    unittest.main()

"""Real SQLite capacity failure in a disposable project, without filling a disk."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from ndtranskripthor.projects.project import Project
from ndtranskripthor.core.app_errors import classify


class AcceptanceStorageTest(unittest.TestCase):
    def test_sqlite_full_rolls_back_revision_and_can_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            with Project(Path(folder)/'project', create=True) as project:
                project.initialize('synthetic.wav', {}, {}, [], 16000)
                project.commit_chunk(0, [dict(start=0, end=1, text='Originál č 日本', words=[])], 'sk')
                project.finish()
                original = project.segments()
                edited = project.segments()
                edited[0]['text'] = 'Uložená oprava'
                project.edit(edited)
                saved = project.segments()
                revision_count = project.db.execute('SELECT count(*) FROM transcript_revisions').fetchone()[0]
                pages = project.db.execute('PRAGMA page_count').fetchone()[0]
                project.db.execute(f'PRAGMA max_page_count={pages}')
                pending = project.segments()
                pending[0]['text'] = 'Nová oprava č 日本. ' * 10000
                with self.assertRaises(sqlite3.DatabaseError) as caught:
                    project.edit(pending)
                self.assertEqual(caught.exception.sqlite_errorcode, sqlite3.SQLITE_FULL)
                self.assertEqual(classify(caught.exception)['category'], 'disk')
                self.assertEqual(project.segments(), saved)
                self.assertEqual(project.db.execute('SELECT count(*) FROM transcript_revisions').fetchone()[0], revision_count)
                self.assertEqual(project.db.execute('PRAGMA quick_check').fetchone(), ('ok',))
                project.db.execute(f'PRAGMA max_page_count={pages+4096}')
                project.edit(pending)
                self.assertEqual(project.segments()[0]['text'], pending[0]['text'])
            with Project(Path(folder)/'project') as reopened:
                self.assertEqual(reopened.segments()[0]['text'], pending[0]['text'])
                self.assertEqual(reopened.segments(view='original'), original)

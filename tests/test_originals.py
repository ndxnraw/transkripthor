"""F04: immutable ASR output, revisions and conservative legacy migration."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import numpy as np
from jobs import job_settings, transcribe_job
from project import Project, fingerprint
from state import atomic_text


class OriginalTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)/'project'
        self.source = Path(self.temp.name)/'audio.wav'
        self.source.write_bytes(b'audio')
        self.settings = job_settings('small', 'sk')
        self.segment = dict(start=0, end=1, text='Originál.', language='sk', words=[], speaker='')

    def create(self, complete=True):
        with Project(self.folder, create=True) as project:
            project.initialize(self.source, fingerprint(self.source), self.settings,
                               [[0, 16000], [16000, 32000]], 32000)
            project.commit_chunk(0, [self.segment], 'sk')
            if complete:
                project.finish()
            project.export(view='original')

    def legacy(self):
        self.folder.mkdir()
        with closing(sqlite3.connect(self.folder/'projekt.sqlite3')) as db:
            db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE segments (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
            for key, value in dict(schema=1, source=str(self.source), fingerprint=fingerprint(self.source),
                    settings=self.settings, plan=[[0,16000],[16000,32000]], samples=32000,
                    next_chunk=1, complete=False).items():
                db.execute('INSERT INTO metadata VALUES (?, ?)', (key, json.dumps(value)))
            db.execute('INSERT INTO segments VALUES (7, ?)', (json.dumps(dict(self.segment, text='Staršia oprava.')),))
            db.commit()
        for name in ('prepis.txt', 'titulky.srt', 'prepis.opravene.txt', 'titulky.partial.srt'):
            (self.folder/name).write_bytes(('Zachovať '+name).encode())

    def test_original_and_each_revision_remain_separate(self):
        self.create()
        originals = {name:(self.folder/name).read_bytes() for name in ('prepis.txt', 'titulky.srt')}
        with Project(self.folder) as project:
            rows = project.segments()
            rows[0].update(text='Prvá oprava.', speaker='Daniel')
            first = project.edit(rows)
            rows[0]['text'] = 'Druhá oprava.'
            second = project.edit(rows)
            project.export(view='revision', revision=first)
            self.assertIn('Prvá oprava.', (self.folder/'prepis.opravene.txt').read_text(encoding='utf-8-sig'))
            project.export(view='revision', revision=second)
            project.export(view='original')
            project.export()  # backward compatible default must also be safe
            self.assertEqual(project.segments('original')[0]['text'], 'Originál.')
            self.assertEqual(project.segments('revision', first)[0]['text'], 'Prvá oprava.')
            with self.assertRaises(sqlite3.IntegrityError):
                project.db.execute("UPDATE original_segments SET data='{}'")
            project.db.rollback()
        with Project(self.folder) as project:
            self.assertEqual(project.segments()[0]['text'], 'Druhá oprava.')
            self.assertEqual(project.segments('original')[0]['speaker'], '')
        for name, content in originals.items():
            self.assertEqual((self.folder/name).read_bytes(), content)

    def test_failed_srt_export_retry_and_completed_job_use_original(self):
        self.create()
        original = (self.folder/'prepis.txt').read_bytes()
        with Project(self.folder) as project:
            rows = project.segments()
            rows[0]['text'] = 'Opravené.'
            revision = project.edit(rows)
            def write(path, *args):
                if path.suffix == '.srt':
                    raise OSError('locked SRT')
                return atomic_text(path, *args)
            with patch('project.atomic_text', side_effect=write):
                with self.assertRaisesRegex(OSError, 'locked SRT'):
                    project.export(view='revision', revision=revision)
            self.assertEqual(project.segments('revision', revision)[0]['text'], 'Opravené.')
            project.export(view='revision', revision=revision)
        self.assertTrue(transcribe_job(Mock(), self.source, self.folder, self.settings,
                                      threading.Event(), Mock(), resume=True))
        self.assertEqual((self.folder/'prepis.txt').read_bytes(), original)
        self.assertIn('Opravené.', (self.folder/'prepis.opravene.txt').read_text(encoding='utf-8-sig'))

    def test_resume_appends_original_without_overwriting_saved_edits(self):
        self.create(complete=False)
        with Project(self.folder) as project:
            rows = project.segments()
            rows[0]['text'] = 'Oprava prvého.'
            revision = project.edit(rows)
        model = Mock()
        model.transcribe.return_value = (iter([SimpleNamespace(start=0, end=1, text='Druhý.', words=[])]),
                                         SimpleNamespace(language='sk'))
        with patch('pcm_audio.decode_audio', return_value=np.zeros(32000)):
            self.assertTrue(transcribe_job(model, self.source, self.folder, self.settings,
                                          threading.Event(), Mock(), resume=True))
        with Project(self.folder) as project:
            self.assertEqual([s['text'] for s in project.segments('original')], ['Originál.', 'Druhý.'])
            self.assertEqual([s['text'] for s in project.segments()], ['Oprava prvého.', 'Druhý.'])
            self.assertEqual(len(project.segments('revision', revision)), 1)
        self.assertNotIn('Oprava', (self.folder/'prepis.txt').read_text(encoding='utf-8-sig'))

    def test_legacy_backup_unknown_origin_and_idempotent_migration(self):
        self.legacy()
        before = {p.name:p.read_bytes() for p in self.folder.iterdir()}
        with Project(self.folder) as project:
            self.assertFalse(project.original_available())
            self.assertEqual(project.segments()[0]['id'], 7)
            self.assertEqual(project.segments('revision', 1)[0]['text'], 'Staršia oprava.')
            self.assertTrue(project.export(view='original'))
            with self.assertRaisesRegex(ValueError, 'cannot be verified'):
                project.segments('original')
        backups = list(self.folder.glob('zaloha-pred-reviziami-*'))
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups[0]/'projekt.sqlite3')) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='original_segments'").fetchone())
            self.assertIn('Star', json.loads(db.execute('SELECT data FROM segments').fetchone()[0])['text'])
        for name, content in before.items():
            if name != 'projekt.sqlite3':
                self.assertEqual((self.folder/name).read_bytes(), content)
                self.assertEqual((backups[0]/name).read_bytes(), content)
        with Project(self.folder) as project:
            project.commit_chunk(1, [dict(self.segment, start=1, end=2, text='Nové.')], 'sk')
            project.finish()
            self.assertTrue(project.export(view='original'))
            project.export(view='revision', revision=project.edit(project.segments()))
            self.assertFalse(project.original_available())
        self.assertEqual((self.folder/'prepis.txt').read_bytes(), before['prepis.txt'])
        self.assertEqual(len(list(self.folder.glob('zaloha-pred-reviziami-*'))), 1)

    def test_backup_failure_does_not_migrate_or_change_exports(self):
        self.legacy()
        before = (self.folder/'projekt.sqlite3').read_bytes()
        with patch('project.shutil.copy2', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError, 'disk full'):
                Project(self.folder)
        self.assertEqual((self.folder/'projekt.sqlite3').read_bytes(), before)
        with Project(self.folder) as project:
            self.assertFalse(project.original_available())

    def test_migration_transaction_rolls_back(self):
        self.legacy()
        with patch.object(Project, 'segments', side_effect=RuntimeError('migration interrupted')):
            with self.assertRaisesRegex(RuntimeError, 'migration interrupted'):
                Project(self.folder)
        with closing(sqlite3.connect(self.folder/'projekt.sqlite3')) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='transcript_storage'").fetchone())
        with Project(self.folder) as project:
            self.assertEqual(project.segments('revision', 1)[0]['id'], 7)

    def test_process_crash_during_migration_can_retry_from_backup(self):
        self.legacy()
        code = '''
import os, sys
from project import Project
Project.segments = lambda *args, **kwargs: os._exit(27)
Project(sys.argv[1])
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.folder)], capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1] / 'src')
        self.assertEqual(result.returncode, 27, result.stderr)
        with closing(sqlite3.connect(self.folder/'projekt.sqlite3')) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='transcript_storage'").fetchone())
        backup = next(self.folder.glob('zaloha-pred-reviziami-*'))
        with closing(sqlite3.connect(backup/'projekt.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM segments').fetchone()[0], 1)
        with Project(self.folder) as project:
            self.assertFalse(project.original_available())
            self.assertEqual(project.segments()[0]['text'], 'Staršia oprava.')

    def test_backup_includes_committed_wal_data(self):
        self.legacy()
        with closing(sqlite3.connect(self.folder/'projekt.sqlite3')) as writer:
            writer.execute('PRAGMA journal_mode=WAL')
            writer.execute('INSERT INTO metadata VALUES (?, ?)', ('wal_test', json.dumps('Committed WAL')))
            writer.commit()
            with Project(self.folder):
                pass
            backup = next(self.folder.glob('zaloha-pred-reviziami-*'))
            with closing(sqlite3.connect(backup/'projekt.sqlite3')) as db:
                self.assertEqual(json.loads(db.execute("SELECT value FROM metadata WHERE key='wal_test'").fetchone()[0]), 'Committed WAL')


if __name__ == '__main__':
    unittest.main()

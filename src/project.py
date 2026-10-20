"""Transactional checkpoint per complete audio chunk; editable full transcript."""
from i18n import tr
from app_errors import ProjectConflict
import hashlib
import json
import sqlite3
import shutil
import uuid
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
from state import atomic_text
from subtitles import render_srt, SubtitleOptions


def fingerprint(source, stop=None):
    path = Path(source)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            if stop and stop.is_set():
                raise InterruptedError(tr('project.fingerprint.recording_check_interrupted'))
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ProjectConflict(tr('project.fingerprint.the_recording_changed_while_being_read'))
    return dict(size=after.st_size, sha256=digest.hexdigest())


class Project:
    def __init__(self, folder, create=False):
        self.folder = Path(folder)
        if create:
            self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / 'projekt.sqlite3'
        if not create and not path.is_file():
            raise ProjectConflict(tr('project.init.projekt_sqlite_is_missing_older_txt_srt_files_do'))
        from ownership import Lease
        self.lease = Lease(self.folder/'.project.lock')
        self.db = sqlite3.connect(path, timeout=15)
        self.db.execute('PRAGMA synchronous=FULL')
        fresh = not self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
        if create or not self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1").fetchone():
            with self.db:
                self.db.execute('BEGIN IMMEDIATE')
                self.db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                self.db.execute('CREATE TABLE IF NOT EXISTS segments (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
        try:
            self._ensure_storage(fresh)
        except BaseException:
            self.db.close()
            self.lease.close()
            raise

    def _ensure_storage(self, fresh):
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='transcript_storage'").fetchone():
            if self.db.execute('SELECT version FROM transcript_storage').fetchone() != (1,):
                raise ProjectConflict(tr('project.ensure_storage.unsupported_transcript_storage_version'))
            return
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            # Recheck after acquiring the writer lock (another process may have migrated).
            if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='transcript_storage'").fetchone():
                return
            if not fresh:
                backup = self.folder / ('zaloha-pred-reviziami-' + uuid.uuid4().hex)
                backup.mkdir()
                # A separate reader sees the last committed state, including WAL data.
                with closing(sqlite3.connect(self.folder/'projekt.sqlite3')) as reader:
                    with closing(sqlite3.connect(backup/'projekt.sqlite3')) as saved:
                        reader.backup(saved)
                        if saved.execute('PRAGMA quick_check').fetchone() != ('ok',):
                            raise OSError(tr('project.ensure_storage.the_project_backup_could_not_be_verified_migration_was'))
                for pattern in ('prepis*.txt', 'titulky*.srt'):
                    for source in self.folder.glob(pattern):
                        shutil.copy2(source, backup/source.name)
                atomic_text(backup/'ZALOHA-DOKONCENA.txt',
                            'Záloha databázy a existujúcich TXT/SRT pred oddelením originálu a revízií.\n', 'utf-8')
            unknown = bool(self.db.execute('SELECT 1 FROM segments LIMIT 1').fetchone()
                           or self.get('next_chunk', 0) or self.get('complete', False))
            self.db.execute('CREATE TABLE transcript_storage (version INTEGER NOT NULL, original_unknown INTEGER NOT NULL)')
            self.db.execute('INSERT INTO transcript_storage VALUES (1, ?)', (int(unknown),))
            self.db.execute('CREATE TABLE original_segments (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
            self.db.execute('CREATE TABLE transcript_revisions (id INTEGER PRIMARY KEY, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, data TEXT NOT NULL)')
            if unknown:
                self.db.execute('INSERT INTO transcript_revisions (data) VALUES (?)',
                                (json.dumps(self.segments(), ensure_ascii=False),))
            for operation in ('UPDATE', 'DELETE'):
                for table in ('original_segments', 'transcript_revisions'):
                    self.db.execute(f"CREATE TRIGGER protect_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'Transcript history is immutable'); END")

    def original_available(self):
        return not self.db.execute('SELECT original_unknown FROM transcript_storage').fetchone()[0]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.db.close()
        self.lease.close()

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO metadata VALUES (?, ?)', (key, json.dumps(value, ensure_ascii=False)))

    def phase(self):
        return self.get('phase', 'complete' if self.get('complete') else
                        ('ready' if self.get('plan') is not None else 'preparing'))

    def begin_preparation(self, source, settings):
        path = Path(source).resolve()
        stat = path.stat()
        identity = dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns)
        # Recover only an empty legacy shell. Never reset existing transcript data.
        if self.get('schema') is None:
            if self.db.execute('SELECT COUNT(*) FROM segments').fetchone()[0] or self.db.execute('SELECT COUNT(*) FROM metadata').fetchone()[0]:
                raise ProjectConflict(tr('project.begin_preparation.project_metadata_is_incomplete_preserve_the_project_and_start'))
            with self.db:
                for key, value in dict(schema=1, source=str(path), source_stat=identity,
                        settings=settings, phase='preparing', preparation_stage='hashing',
                        next_chunk=0, complete=False).items():
                    self.put(key, value)
        else:
            if self.get('schema') != 1 or self.get('settings') != settings:
                raise ProjectConflict(tr('project.begin_preparation.the_model_language_or_settings_have_changed_restore_the'))
            if self.phase() == 'preparing':
                if self.get('source') != str(path) or self.get('source_stat') != identity:
                    raise ProjectConflict(tr('project.begin_preparation.the_source_recording_has_changed_since_preparation_started_start'))
                if self.get('next_chunk', 0) or self.db.execute('SELECT COUNT(*) FROM segments').fetchone()[0]:
                    raise ProjectConflict(tr('project.begin_preparation.invalid_project_preparation_state_start_a_new_transcription_in'))

    def preparation_stage(self, stage, digest=None):
        with self.db:
            self.put('preparation_stage', stage)
            if digest is not None:
                self.put('fingerprint', digest)

    def start_transcription(self):
        with self.db:
            self.put('phase', 'transcribing')

    def initialize(self, source, digest, settings, plan, samples):
        with self.db:
            if self.get('subtitle_options') is None:
                self.put('subtitle_options', asdict(self.subtitle_options()))
            for key, value in dict(schema=1, source=str(Path(source).resolve()), fingerprint=digest,
                settings=settings, plan=plan, samples=samples, next_chunk=0, complete=False,
                phase='ready', preparation_stage=None).items():
                self.put(key, value)

    def editor_problem(self):
        if self.get('schema') != 1 or not isinstance(self.get('source'), str) or not self.get('source'):
            return tr('project.editor_problem.this_project_has_no_valid_editor_data_yet_resume')
        if self.phase() == 'preparing':
            return tr('project.editor_problem.recording_preparation_was_interrupted_transcription_has_not_started_select')
        rows = self.segments()
        if not rows:
            return (tr('result.no_speech') + '\n' + tr('result.no_speech_help')
                    if self.get('complete') else tr('project.editor_problem.no_text_has_been_saved_in_this_project_yet'))
        if any(not isinstance(s.get('text'), str) or not isinstance(s.get('start'), (int, float))
               or not isinstance(s.get('end'), (int, float)) or not 0 <= s['start'] < s['end'] for s in rows):
            return tr('project.editor_problem.the_project_contains_invalid_segments_the_editor_cannot_safely')
        return None

    def verify(self, digest, settings):
        if self.get('schema') != 1 or self.get('fingerprint') != digest:
            raise ProjectConflict(tr('project.verify.the_recording_does_not_match_the_saved_project_start'))
        if self.get('settings') != settings:
            raise ProjectConflict(tr('project.verify.the_model_language_or_settings_have_changed_restore_the'))

    def segments(self, view='current', revision=None):
        if view == 'revision':
            layers, seen = [], set()
            while True:
                if revision in seen:
                    raise ProjectConflict('Invalid transcript revision chain')
                seen.add(revision)
                row = self.db.execute('SELECT data FROM transcript_revisions WHERE id=?', (revision,)).fetchone()
                if row is None:
                    raise ProjectConflict(tr('project.segments.the_requested_saved_revision_does_not_exist'))
                data = json.loads(row[0])
                if isinstance(data, list):
                    result = {item['id']: item for item in data}
                    break
                layers.append(data['changes'])
                revision = data['base']
            for changes in reversed(layers):
                result.update((item['id'], item) for item in changes)
            return [result[key] for key in sorted(result)]
        if view not in ('current', 'original'):
            raise ProjectConflict(tr('project.segments.invalid_transcript_selection'))
        if view == 'original' and not self.original_available():
            raise ProjectConflict(tr('project.segments.the_original_model_output_cannot_be_verified_in_this'))
        table = 'original_segments' if view == 'original' else 'segments'
        return [dict(json.loads(data), id=identifier) for identifier, data in
                self.db.execute(f'SELECT id, data FROM {table} ORDER BY id')]

    def commit_chunk(self, index, segments, previous_language):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if self.get('next_chunk') != index:
                raise ProjectConflict(tr('project.commit_chunk.invalid_resume_point_the_segment_was_already_saved_or'))
            identifier = self.db.execute('SELECT COALESCE(MAX(id), -1)+1 FROM segments').fetchone()[0]
            for segment in segments:
                self.db.execute('INSERT INTO original_segments VALUES (?, ?)',
                                (identifier, json.dumps(segment, ensure_ascii=False)))
                self.db.execute('INSERT INTO segments VALUES (?, ?)',
                                (identifier, json.dumps(segment, ensure_ascii=False)))
                identifier += 1
            self.put('next_chunk', index + 1)
            self.put('previous_language', previous_language)
            self.put('phase', 'transcribing')

    def subtitle_options(self):
        """Project profile; older revisions stored it only in the export request."""
        options = self.get('subtitle_options')
        if options is None:
            request = self.get('editor_export') or {}
            options = request.get('options')
        return SubtitleOptions(**options) if options is not None else SubtitleOptions()

    def edit(self, segments, export_options=None):
        options = asdict(export_options if export_options is not None else self.subtitle_options())
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            for segment in segments:
                existing = self.db.execute('SELECT data FROM segments WHERE id=?', (segment['id'],)).fetchone()
                if existing and dict(json.loads(existing[0]), id=segment['id']) == segment:
                    continue
                cursor = self.db.execute('UPDATE segments SET data=? WHERE id=?',
                                         (json.dumps(segment, ensure_ascii=False), segment['id']))
                if cursor.rowcount != 1:
                    raise ProjectConflict(tr('project.edit.the_segment_being_edited_no_longer_exists_in_the'))
            current = self.segments()
            previous = self.db.execute('SELECT MAX(id) FROM transcript_revisions').fetchone()[0]
            if previous is None:
                snapshot = current  # First immutable baseline; older full revisions stay readable.
            else:
                baseline = {item['id']: item for item in self.segments('revision', previous)}
                snapshot = dict(base=previous, changes=[item for item in current if baseline.get(item['id']) != item])
            cursor = self.db.execute('INSERT INTO transcript_revisions (data) VALUES (?)',
                                     (json.dumps(snapshot, ensure_ascii=False),))
            self.put('subtitle_options', options)
            self.put('editor_export', dict(revision=cursor.lastrowid, state='pending', options=options))
            return cursor.lastrowid

    def retry_export(self):
        request = self.get('editor_export')
        if not request:
            raise ProjectConflict(tr('project.retry_export.save_the_project_changes_first'))
        return self.export(SubtitleOptions(**request['options']), view='revision', revision=request['revision'])

    def result(self):
        table = 'original_segments' if self.original_available() else 'segments'
        count = self.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
        return dict(outcome='transcribed' if count else 'no_speech', segment_count=count)

    def finish(self):
        with self.db:
            self.put('result', self.result())
            self.put('complete', True)
            self.put('phase', 'complete')

    def export(self, options=None, corrected=False, *, view=None, revision=None):
        # Keep the old API safe; application callers explicitly select their source.
        view = view or ('revision' if corrected else 'original')
        if view == 'original' and not self.original_available():
            return [tr('project.export.the_original_model_output_cannot_be_verified_in_this')]
        if view == 'revision' and revision is None:
            if not corrected:
                raise ProjectConflict(tr('project.export.select_a_saved_revision_to_export_corrections'))
            revision = self.db.execute('SELECT MAX(id) FROM transcript_revisions').fetchone()[0]
        if view not in ('original', 'revision'):
            raise ProjectConflict(tr('project.export.export_requires_the_original_or_a_saved_revision'))
        request = self.get('editor_export')
        if view == 'revision' and request and request['revision'] == revision:
            with self.db:
                self.put('editor_export', dict(request, state='pending'))
        segments = self.segments(view, revision)
        from speech_models import SAMPLE_RATE
        samples = self.get('samples')
        srt, warnings = render_srt(segments, options,
                                  audio_duration=samples / SAMPLE_RATE if samples is not None else None)
        suffix = '.opravene' if view == 'revision' else ('' if self.get('complete') else '.partial')
        from export_pair import publish_pair
        location = publish_pair(self.folder, suffix,
            ''.join(s['text'].strip()+'\n' for s in segments if s['text'].strip()), srt,
            dict(view=view, revision=revision, next_chunk=self.get('next_chunk')), write=atomic_text)
        request = self.get('editor_export')
        if view == 'revision' and request and request['revision'] == revision:
            with self.db:
                self.put('editor_export', dict(request, state='complete', directory=str(location)))
        return warnings

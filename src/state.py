"""Atómové nastavenia a fronta; žiadne údaje neopúšťajú počítač."""
from i18n import tr
import json
import os
import re
import uuid
import sqlite3
from pathlib import Path

STATES = ('waiting', 'processing', 'completed', 'interrupted', 'failed')
LEGACY_STATES = {'čaká': 'waiting', 'spracúva sa': 'processing', 'hotovo': 'completed',
                 'prerušené': 'interrupted', 'chyba': 'failed'}


def atomic_text(path, text, encoding='utf-8'):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('w', encoding=encoding) as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class StateStore:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.warning = ''

    def read(self, name, default):
        path = self.folder / name
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return default
        except (OSError, ValueError):
            self.warning = tr('state.read.could_not_read_default_values_are_being_used', p0=name)
            # Preserve evidence rather than overwriting a damaged file on exit.
            if path.exists():
                try:
                    path.rename(path.with_name(path.name + '.damaged-' + uuid.uuid4().hex[:8]))
                except OSError:
                    pass
            return default

    def save(self, name, value):
        if name == 'queue.json':
            return self.save_queue(value)
        atomic_text(self.folder / name, json.dumps(value, ensure_ascii=False, indent=2))

    def save_queue(self, items):
        """Atomic ordered queue; unchanged records are never rewritten."""
        self.folder.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.folder/'queue.sqlite3', timeout=1)
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('CREATE TABLE IF NOT EXISTS queue (id TEXT PRIMARY KEY, position INTEGER NOT NULL, data TEXT NOT NULL)')
                old = {key: (position, data) for key, position, data in db.execute('SELECT * FROM queue')}
                for position, item in enumerate(items):
                    key = item['id']
                    value = (position, json.dumps(item, ensure_ascii=False))
                    if old.pop(key, None) != value:
                        db.execute('INSERT OR REPLACE INTO queue VALUES (?, ?, ?)', (key, *value))
                db.executemany('DELETE FROM queue WHERE id=?', ((key,) for key in old))
        finally:
            db.close()

    def settings(self, languages, models):
        raw = self.read('settings.json', {})
        raw = raw if isinstance(raw, dict) else {}
        from i18n import normalize_language
        result = {'ui_language': normalize_language(raw.get('ui_language'))}
        for key, choices in [('language', languages), ('model', models), ('theme', ('light', 'dark')), ('device', ('cpu', 'cuda'))]:
            if isinstance(raw.get(key), str) and raw[key] in choices:
                result[key] = raw[key]
        for key in ('offline', 'autoplay'):
            if isinstance(raw.get(key), bool):
                result[key] = raw[key]
        if isinstance(raw.get('output'), str) and raw['output'].strip():
            result['output'] = raw['output']
        if isinstance(raw.get('geometry'), str) and re.fullmatch(r'\d{3,5}x\d{3,5}(?:[+-]\d+[+-]\d+)?', raw['geometry']):
            result['geometry'] = raw['geometry']
        return result

    def save_settings(self, values):
        previous = self.read('settings.json', {})
        merged = dict(previous) if isinstance(previous, dict) else {}
        merged.update(values)
        self.save('settings.json', merged)

    def queue(self):
        database = self.folder/'queue.sqlite3'
        if database.exists():
            db = sqlite3.connect(database, timeout=1)
            try:
                initialized = db.execute("SELECT 1 FROM sqlite_master WHERE name='queue'").fetchone()
                raw = ([json.loads(row[0]) for row in db.execute('SELECT data FROM queue ORDER BY position')]
                       if initialized else self.read('queue.json', []))
            finally:
                db.close()
        else:
            initialized = False
            raw = self.read('queue.json', [])
        result, ids = [], set()
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict) or not isinstance(item.get('source'), str):
                continue
            identifier = item.get('id')
            if not isinstance(identifier, str) or identifier in ids:
                identifier = uuid.uuid4().hex
            ids.add(identifier)
            status = item.get('state', 'waiting')
            if not isinstance(status, str):
                status = 'waiting'
            status = LEGACY_STATES.get(status, status)
            if status == 'processing':
                status = 'interrupted'
            result.append(dict(id=identifier, source=item['source'],
                state=status if status in STATES else 'waiting',
                project=item.get('project') if isinstance(item.get('project'), str) else '',
                error=item.get('error') if isinstance(item.get('error'), str) else ''))
        # The old JSON is kept as an untouched migration backup. A transaction
        # either publishes the whole normalized queue or leaves it available.
        if not initialized:
            self.save_queue(result)
        return result


def queue_item(source):
    return dict(id=uuid.uuid4().hex, source=str(Path(source).resolve()), state='waiting', project='', error='')


class ProgressClock:
    """ETA only after measurable work; loading/download time is excluded."""
    def __init__(self, now):
        self.started = now
        self.samples = []

    def update(self, fraction, now):
        if not self.samples or fraction > self.samples[-1][1]:
            self.samples.append((now, fraction))
            self.samples = self.samples[-50:]

    def remaining(self, now):
        if len(self.samples) < 3:
            return None
        elapsed = self.samples[-1][0] - self.samples[0][0]
        advance = self.samples[-1][1] - self.samples[0][1]
        if elapsed < 10 or advance < 0.02:
            return None
        return max(0, (1 - self.samples[-1][1]) * elapsed / advance - (now - self.samples[-1][0]))

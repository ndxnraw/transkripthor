"""Atómové nastavenia a fronta; žiadne údaje neopúšťajú počítač."""
from i18n import tr
import json
import os
import re
import uuid
import sqlite3
import math
from app_errors import CATEGORIES
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
            if item.get('error_category') in CATEGORIES:
                result[-1]['error_category'] = item['error_category']
            if item.get('outcome') in ('no_speech', 'transcribed'):
                result[-1]['outcome'] = item['outcome']
                count = item.get('segment_count', 0)
                result[-1]['segment_count'] = max(0, count) if isinstance(count, int) else 0
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
        if elapsed < 10 or advance < 0.02 or now - self.samples[-1][0] >= 30:
            return None
        # Time passing without new checkpoints is not completed audio.
        return max(0, (1 - self.samples[-1][1]) * elapsed / advance)


class BatchProgress:
    """Audio coverage and queue outcomes are independent measures."""
    def __init__(self, identifiers):
        self.durations = dict.fromkeys(identifiers)
        self.fractions = dict.fromkeys(identifiers, 0.)
        self.states = dict.fromkeys(identifiers, 'waiting')

    def duration(self, identifier, seconds):
        if identifier in self.durations:
            self.durations[identifier] = (float(seconds) if isinstance(seconds, (int, float))
                and math.isfinite(seconds) and seconds >= 0 else None)

    def progress(self, identifier, percent):
        if identifier in self.fractions and math.isfinite(percent):
            self.fractions[identifier] = max(0., min(1., percent / 100))

    def state(self, identifier, state):
        if identifier in self.states:
            self.states[identifier] = state
            if state == 'completed':
                self.fractions[identifier] = 1.

    def fraction(self):
        if not self.durations or any(value is None for value in self.durations.values()):
            return None
        total = sum(self.durations.values())
        if total == 0:
            return None
        return sum(seconds*self.fractions[key] for key, seconds in self.durations.items())/total

    def counts(self):
        return {state: sum(value == state for value in self.states.values())
                for state in ('completed', 'failed', 'interrupted')}

"""Bounded, immutable field deltas for one open project's editing session."""
import json


class EditHistory:
    def __init__(self, max_operations=200, max_bytes=16 * 1024 * 1024):
        self.max_operations, self.max_bytes = max_operations, max_bytes
        self.entries = []
        self.cursor = self.bytes = self.state = self.saved = self.serial = 0

    @property
    def dirty(self):
        return self.state != self.saved

    def mark_saved(self):
        self.saved = self.state

    def record(self, changes):
        if not changes:
            return True
        payload = json.dumps(changes, ensure_ascii=False).encode('utf-8')
        del self.entries[self.cursor:]
        self.bytes = sum(len(entry[2]) for entry in self.entries)
        self.serial += 1
        self.entries.append((self.state, self.serial, payload))
        self.state = self.serial
        self.bytes += len(payload)
        retained = len(payload) <= self.max_bytes
        while self.entries and (self.bytes > self.max_bytes or len(self.entries) > self.max_operations):
            self.bytes -= len(self.entries.pop(0)[2])
        self.cursor = len(self.entries)
        return retained

    def step(self, redo=False):
        if redo:
            if self.cursor == len(self.entries):
                return None
            entry = self.entries[self.cursor]
            self.cursor += 1
            self.state = entry[1]
        else:
            if not self.cursor:
                return None
            self.cursor -= 1
            entry = self.entries[self.cursor]
            self.state = entry[0]
        return [(identifier, after if redo else before)
                for identifier, before, after in json.loads(entry[2])]

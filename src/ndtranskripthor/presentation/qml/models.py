"""Virtualized Qt models; edits notify a single row without resetting selection."""
from pathlib import Path
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
from ndtranskripthor.core.i18n import tr


class Rows(QAbstractListModel):
    def __init__(self, fields, parent=None):
        super().__init__(parent)
        self.fields = fields
        self.rows = []

    def roleNames(self):
        return {Qt.UserRole+i+1: name.encode() for i, name in enumerate(self.fields)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role):
        position = role-Qt.UserRole-1
        if not index.isValid() or not 0 <= index.row() < len(self.rows) or not 0 <= position < len(self.fields):
            return None
        row, name = self.rows[index.row()], self.fields[position]
        if name == 'fileName': return Path(row['source']).name
        if name == 'stateLabel': return tr('result.no_speech' if row.get('outcome') == 'no_speech' else 'queue.'+row['state'])
        return row.get({'bodyText':'text', 'jobState':'state', 'rowId':'id', 'modelId':'model', 'availability':'state'}.get(name, name), '')

    def replace(self, rows):
        if 'rowId' in self.fields and [row['id'] for row in rows] == [row['id'] for row in self.rows]:
            self.rows = rows
            if rows: self.dataChanged.emit(self.index(0), self.index(len(rows)-1), list(self.roleNames()))
            return
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def notify(self, index):
        self.dataChanged.emit(self.index(index), self.index(index), list(self.roleNames()))

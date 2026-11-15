"""Stable Qt roles for the downloaded and online Practice grids."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class PracticePackModel(QAbstractListModel):
    _FIELDS = (
        ("packId", "id", ""),
        ("packVersion", "version", 0),
        ("packTitle", "title", ""),
        ("packSubject", "subject", ""),
        ("packChapter", "chapter", ""),
        ("packTopic", "topic", ""),
        ("packQuestionCount", "questionCount", 0),
        ("packInstalled", "isInstalled", False),
        ("packDownloading", "isDownloading", False),
        ("packStatus", "status", ""),
        ("packRetry", "retry", False),
    )
    _FIRST_ROLE = int(Qt.ItemDataRole.UserRole) + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def roleNames(self):
        return {self._FIRST_ROLE + i: name.encode("ascii")
                for i, (name, _, _) in enumerate(self._FIELDS)}

    def rowCount(self, parent=None):
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        column = role - self._FIRST_ROLE
        if index.isValid() and 0 <= index.row() < len(self._rows) and 0 <= column < len(self._FIELDS):
            return self._rows[index.row()][column]
        return None

    def set_rows(self, packs):
        rows = [tuple(pack.get(field, default) for _, field, default in self._FIELDS) for pack in packs]
        if rows == self._rows:
            return
        old_count, new_count = len(self._rows), len(rows)
        shared = min(old_count, new_count)
        if any(self._rows[i][:2] != rows[i][:2] for i in range(shared)):
            self.beginResetModel()
            self._rows = rows
            self.endResetModel()
            return

        for i in range(shared):
            roles = [self._FIRST_ROLE + j for j, (old, new) in enumerate(zip(self._rows[i], rows[i], strict=True))
                     if old != new]
            if roles:
                self._rows[i] = rows[i]
                index = self.index(i, 0)
                self.dataChanged.emit(index, index, roles)
        if new_count > old_count:
            self.beginInsertRows(QModelIndex(), old_count, new_count - 1)
            self._rows.extend(rows[old_count:])
            self.endInsertRows()
        elif new_count < old_count:
            self.beginRemoveRows(QModelIndex(), new_count, old_count - 1)
            del self._rows[new_count:]
            self.endRemoveRows()

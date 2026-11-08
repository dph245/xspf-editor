from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from playlist import Playlist


class StationModel(QAbstractTableModel):
    fields = ("title", "location")
    headers = ("Sendername", "Stream-URL")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.playlist = Playlist.empty()

    def replace_playlist(self, playlist):
        self.beginResetModel()
        self.playlist = playlist
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.playlist.tracks)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.fields)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role in (
            Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole, Qt.ItemDataRole.ToolTipRole
        ):
            return self.playlist.field(index.row(), self.fields[index.column()])

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        if self.playlist.set_field(index.row(), self.fields[index.column()], value):
            self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsDropEnabled
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def append_station(self):
        row = self.rowCount()
        self.beginInsertRows(QModelIndex(), row, row)
        self.playlist.append_track()
        self.endInsertRows()
        return self.index(row, 0)

    def removeRows(self, row, count, parent=QModelIndex()):
        if parent.isValid() or count != 1 or not 0 <= row < self.rowCount():
            return False
        self.beginRemoveRows(parent, row, row)
        self.playlist.remove_track(row)
        self.endRemoveRows()
        return True

    def moveRows(self, source_parent, source, count, destination_parent, destination):
        if (
            source_parent.isValid() or destination_parent.isValid() or count != 1
            or not 0 <= source < self.rowCount() or not 0 <= destination <= self.rowCount()
            or destination in (source, source + 1)
        ):
            return False
        if not self.beginMoveRows(source_parent, source, source, destination_parent, destination):
            return False
        self.playlist.move_track(source, destination)
        self.endMoveRows()
        return True

from PyQt6.QtCore import QAbstractTableModel, Qt
from PyQt6.QtGui import QColor

from package.enums.latencyenum import LatencyEnum


class ServerTableModel(QAbstractTableModel):
    def __init__(self, data):
        super(ServerTableModel, self).__init__()
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return 6

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        server = self._data[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return server.name
            elif index.column() == 1:
                return str(server)
            elif index.column() == 2:
                return server.game
            elif index.column() == 3:
                return f"{server.player_count} / {server.max_players}"
            elif index.column() == 4:
                return server.map_name
            elif index.column() == 5:
                return server.display_ping_in_ms()
        elif role == Qt.ItemDataRole.UserRole:
            return str(server)
        elif role == Qt.ItemDataRole.ForegroundRole:
            if index.column() == 5:
                if server.ping == LatencyEnum.TIMEOUT:
                    return QColor(Qt.GlobalColor.red)
                elif server.ping > 50:
                    return QColor(Qt.GlobalColor.yellow)
                elif server.ping > 140:
                    return QColor(Qt.GlobalColor.orange)
            elif index.column() == 3:
                if server.max_players - server.reserved_slots <= server.player_count:
                    return QColor(Qt.GlobalColor.red)
                elif server.player_count > 0:
                    return QColor(Qt.GlobalColor.darkGreen)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            headers = ["Name", "Address", "Game", "Players", "Map", "Ping"]
            return headers[section]
        return None

    def update_all_data(self, new_data):
        # Update the entire data
        self.layoutAboutToBeChanged.emit()
        self._data = new_data
        self.layoutChanged.emit()

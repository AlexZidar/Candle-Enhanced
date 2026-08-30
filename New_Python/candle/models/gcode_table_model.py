"""G-Code Program Table Model with execution state tracking."""

from typing import List, Optional, Any
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal
from ..config import GCodeItemState


class GCodeItem:
    def __init__(self, command: str = "", state: int = GCodeItemState.InQueue,
                 response: str = "", line: int = -1, args: Optional[List[str]] = None):
        self.command: str = command
        self.state: int = state
        self.response: str = response
        self.line: int = line
        self.args: List[str] = args if args is not None else []


class GCodeTableModel(QAbstractTableModel):
    commandChanged = pyqtSignal(int, str, str)  # row, old_cmd, new_cmd
    commandsInserted = pyqtSignal(int, list)    # row, commands
    rowAdded = pyqtSignal(int)                  # row

    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_data: List[GCodeItem] = []
        self.m_headers = ["#", "Command", "State", "Response", "Line", "Args"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.m_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.m_headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self.m_data):
            return None

        row = index.row()
        col = index.column()
        item = self.m_data[row]

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0:
                return "" if row == len(self.m_data) - 1 else str(row + 1)
            elif col == 1:
                return item.command
            elif col == 2:
                if row == len(self.m_data) - 1:
                    return ""
                if item.state == GCodeItemState.InQueue:
                    return "In queue"
                elif item.state == GCodeItemState.Sent:
                    return "Sent"
                elif item.state == GCodeItemState.Processed:
                    return "Processed"
                elif item.state == GCodeItemState.Skipped:
                    return "Skipped"
                return "Unknown"
            elif col == 3:
                return item.response
            elif col == 4:
                return item.line if item.line >= 0 else ""
            elif col == 5:
                return " ".join(item.args)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 0:
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or index.row() >= len(self.m_data):
            return False

        row = index.row()
        col = index.column()
        item = self.m_data[row]

        if col == 0:
            return False
        elif col == 1:
            old_command = item.command
            new_command = str(value)
            if new_command != old_command:
                item.command = new_command
                item.args = []
                self.commandChanged.emit(row, old_command, new_command)
        elif col == 2:
            item.state = int(value)
        elif col == 3:
            item.response = str(value)
        elif col == 4:
            item.line = int(value)
        elif col == 5:
            if isinstance(value, list):
                item.args = value
            elif isinstance(value, str):
                item.args = value.split()

        self.dataChanged.emit(index, index, [role, Qt.ItemDataRole.DisplayRole])
        return True

    def setCommand(self, row: int, command: str) -> None:
        if row < len(self.m_data):
            self.m_data[row].command = command
            self.m_data[row].args = []
            idx1 = self.index(row, 1)
            idx5 = self.index(row, 5)
            self.dataChanged.emit(idx1, idx5, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])

    def insertCommands(self, row: int, commands: List[str]) -> None:
        self.insertRows(row, len(commands))
        for i, cmd in enumerate(commands):
            self.setCommand(row + i, cmd)
        self.commandsInserted.emit(row, commands)

    def addRow(self, row: int) -> None:
        self.insertRow(row)
        self.rowAdded.emit(row)

    def insertRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        if row > len(self.m_data):
            return False
        self.beginInsertRows(parent, row, row + count - 1)
        for _ in range(count):
            self.m_data.insert(row, GCodeItem())
        self.endInsertRows()
        return True

    def insertRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        return self.insertRows(row, 1, parent)

    def removeRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        if row + count > len(self.m_data):
            return False
        self.beginRemoveRows(parent, row, row + count - 1)
        del self.m_data[row:row + count]
        self.endRemoveRows()
        return True

    def removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        return self.removeRows(row, 1, parent)

    def clear(self) -> None:
        self.beginResetModel()
        self.m_data.clear()
        self.endResetModel()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.m_headers[section]
        return str(section + 1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if index.column() == 1:
            return super().flags(index) | Qt.ItemFlag.ItemIsEditable
        return super().flags(index)

    def items(self) -> List[GCodeItem]:
        return self.m_data

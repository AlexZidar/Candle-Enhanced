"""Table model representing the heightmap probe grid."""

import math
from typing import List, Any
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal


class HeightMapTableModel(QAbstractTableModel):
    dataChangedByUserInput = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_data: List[List[float]] = []

    def resize(self, cols: int, rows: int) -> None:
        self.beginResetModel()
        self.m_data = [[float('nan')] * cols for _ in range(rows)]
        self.endResetModel()

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        if row >= len(self.m_data) or col >= len(self.m_data[0]):
            return None

        # Display and Edit are visually inverted along Y (top row is highest Y)
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            display_row = (len(self.m_data) - 1) - row
            val = self.m_data[display_row][col]
            return "" if math.isnan(val) else f"{val:.3f}"

        if role == Qt.ItemDataRole.UserRole:
            return self.m_data[row][col]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False

        row = index.row()
        col = index.column()
        if row >= len(self.m_data) or col >= len(self.m_data[0]):
            return False

        try:
            val = float(value)
        except (ValueError, TypeError):
            val = float('nan')

        actual_row = (len(self.m_data) - 1) - row if role == Qt.ItemDataRole.EditRole else row
        self.m_data[actual_row][col] = val

        self.dataChanged.emit(index, index, [role, Qt.ItemDataRole.DisplayRole])

        if role == Qt.ItemDataRole.EditRole:
            self.dataChangedByUserInput.emit()

        return True

    def clear(self) -> None:
        self.beginResetModel()
        self.m_data.clear()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.m_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.m_data[0]) if self.m_data else 0

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        return str(section + 1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable

    def getRawData(self) -> List[List[float]]:
        return self.m_data

    def setRawData(self, data: List[List[float]]) -> None:
        self.beginResetModel()
        self.m_data = data
        self.endResetModel()

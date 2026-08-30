"""Undo and Redo history management for G-Code table editing."""

from typing import List
from PyQt6.QtCore import QObject, pyqtSignal
from .gcode_table_model import GCodeTableModel


class HistoryItem:
    def undo(self) -> None:
        raise NotImplementedError

    def redo(self) -> None:
        raise NotImplementedError


class RowChangedHistoryItem(HistoryItem):
    def __init__(self, model: GCodeTableModel, row: int, old_val: str, new_val: str):
        self.model = model
        self.row = row
        self.old_val = old_val
        self.new_val = new_val

    def undo(self) -> None:
        self.model.setCommand(self.row, self.old_val)

    def redo(self) -> None:
        self.model.setCommand(self.row, self.new_val)


class RowsInsertedHistoryItem(HistoryItem):
    def __init__(self, model: GCodeTableModel, row: int, commands: List[str]):
        self.model = model
        self.row = row
        self.commands = list(commands)

    def undo(self) -> None:
        self.model.removeRows(self.row, len(self.commands))

    def redo(self) -> None:
        self.model.insertCommands(self.row, self.commands)


class RowsRemovedHistoryItem(HistoryItem):
    def __init__(self, model: GCodeTableModel, row: int, commands: List[str]):
        self.model = model
        self.row = row
        self.commands = list(commands)

    def undo(self) -> None:
        self.model.insertCommands(self.row, self.commands)

    def redo(self) -> None:
        self.model.removeRows(self.row, len(self.commands))


class RowAddedHistoryItem(HistoryItem):
    def __init__(self, model: GCodeTableModel, row: int):
        self.model = model
        self.row = row

    def undo(self) -> None:
        self.model.removeRow(self.row)

    def redo(self) -> None:
        self.model.insertRow(self.row)


class TableHistoryManager(QObject):
    historyChanged = pyqtSignal(list, int)  # history labels, current index

    def __init__(self, model: GCodeTableModel, parent=None):
        super().__init__(parent)
        self.m_model = model
        self.m_items: List[HistoryItem] = []
        self.m_currentIndex: int = -1
        self.m_blockUpdates: bool = False
        self.m_rowsAboutToBeRemoved: List[str] = []

        self.m_model.commandChanged.connect(self.onCommandChanged)
        self.m_model.rowAdded.connect(self.onRowAdded)
        self.m_model.commandsInserted.connect(self.onCommandsInserted)

    def canUndo(self) -> bool:
        return self.m_currentIndex >= 0

    def canRedo(self) -> bool:
        return self.m_currentIndex < len(self.m_items) - 1

    def undo(self) -> bool:
        if not self.canUndo():
            return False
        self.m_blockUpdates = True
        self.m_items[self.m_currentIndex].undo()
        self.m_currentIndex -= 1
        self.m_blockUpdates = False
        self.emitHistory()
        return True

    def redo(self) -> bool:
        if not self.canRedo():
            return False
        self.m_blockUpdates = True
        self.m_currentIndex += 1
        self.m_items[self.m_currentIndex].redo()
        self.m_blockUpdates = False
        self.emitHistory()
        return True

    def clear(self) -> None:
        self.m_items.clear()
        self.m_currentIndex = -1
        self.emitHistory()

    def addItem(self, item: HistoryItem) -> None:
        self.m_currentIndex += 1
        if self.m_currentIndex < len(self.m_items):
            self.m_items = self.m_items[:self.m_currentIndex]
        self.m_items.append(item)
        self.emitHistory()

    def emitHistory(self) -> None:
        history: List[str] = []
        for item in self.m_items:
            if isinstance(item, RowAddedHistoryItem):
                history.append("❐")
            elif isinstance(item, RowChangedHistoryItem):
                history.append("✍")
            elif isinstance(item, RowsInsertedHistoryItem):
                history.append("+")
            elif isinstance(item, RowsRemovedHistoryItem):
                history.append("−")
        self.historyChanged.emit(history, self.m_currentIndex)

    def onCommandChanged(self, row: int, old_val: str, new_val: str) -> None:
        if self.m_blockUpdates:
            return
        if row == self.m_model.rowCount() - 1:
            self.addItem(RowsInsertedHistoryItem(self.m_model, row, [new_val]))
        else:
            self.addItem(RowChangedHistoryItem(self.m_model, row, old_val, new_val))

    def onCommandsInserted(self, row: int, commands: List[str]) -> None:
        if self.m_blockUpdates:
            return
        self.addItem(RowsInsertedHistoryItem(self.m_model, row, commands))

    def onRowAdded(self, row: int) -> None:
        if self.m_blockUpdates:
            return
        self.addItem(RowAddedHistoryItem(self.m_model, row))

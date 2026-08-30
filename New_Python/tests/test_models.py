"""Unit tests for table models and undo/redo history."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import Qt
from candle.models.gcode_table_model import GCodeTableModel
from candle.models.table_history import TableHistoryManager


class TestModels(unittest.TestCase):
    def test_gcode_table_model_and_history(self):
        model = GCodeTableModel()
        history = TableHistoryManager(model)

        model.insertCommands(0, ["G0 X0 Y0", "G1 X10 Y10 F500", "G0 Z5"])
        self.assertEqual(model.rowCount(), 3)

        # Edit command
        idx = model.index(1, 1)
        model.setData(idx, "G1 X20 Y20 F600", Qt.ItemDataRole.EditRole)
        self.assertEqual(model.data(idx, Qt.ItemDataRole.DisplayRole), "G1 X20 Y20 F600")

        # Undo
        self.assertTrue(history.canUndo())
        history.undo()
        self.assertEqual(model.data(idx, Qt.ItemDataRole.DisplayRole), "G1 X10 Y10 F500")

        # Redo
        self.assertTrue(history.canRedo())
        history.redo()
        self.assertEqual(model.data(idx, Qt.ItemDataRole.DisplayRole), "G1 X20 Y20 F600")


if __name__ == "__main__":
    unittest.main()

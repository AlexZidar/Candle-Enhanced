"""Unit tests for heightmap interpolation, manager, and table model."""

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QRectF, Qt
from candle.heightmap.interpolation import Interpolation
from candle.heightmap.heightmap_model import HeightMapTableModel
from candle.heightmap.heightmap_manager import HeightMapManager, HeightMapData


class TestHeightMap(unittest.TestCase):
    def test_bicubic_interpolation_flat(self):
        # 4x4 flat surface at Z = 1.5
        grid = [[1.5] * 4 for _ in range(4)]
        rect = QRectF(0, 0, 100, 100)
        z = Interpolation.bicubicInterpolate(rect, grid, 50, 50)
        self.assertAlmostEqual(z, 1.5, places=3)

    def test_heightmap_model_and_io(self):
        model = HeightMapTableModel()
        model.resize(3, 3)
        self.assertEqual(model.columnCount(), 3)
        self.assertEqual(model.rowCount(), 3)

        # Set center point
        idx = model.index(1, 1)
        model.setData(idx, 0.456, Qt.ItemDataRole.EditRole)
        self.assertAlmostEqual(float(model.data(idx, Qt.ItemDataRole.DisplayRole)), 0.456, places=3)

        # Save and load .map
        data = HeightMapData()
        data.borderRect = QRectF(10, 20, 80, 60)
        data.gridX = 3
        data.gridY = 3

        with tempfile.NamedTemporaryFile(suffix=".map", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            saved = HeightMapManager.saveHeightMap(tmp_path, data, model)
            self.assertTrue(saved)

            loaded = HeightMapManager.loadHeightMap(tmp_path)
            self.assertIsNotNone(loaded)
            loaded_data, loaded_grid = loaded
            self.assertEqual(loaded_data.gridX, 3)
            self.assertEqual(loaded_data.gridY, 3)
            self.assertAlmostEqual(loaded_data.borderRect.width(), 80.0, places=2)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_probe_program_generation(self):
        rect = QRectF(0, 0, 50, 50)
        cmds = HeightMapManager.generateProbeProgram(rect, 3, 3, 2.0, -2.0, 25.0, 0, 0)
        self.assertGreater(len(cmds), 10)
        self.assertTrue(any("G38.2" in c for c in cmds))


if __name__ == "__main__":
    unittest.main()

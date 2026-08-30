"""GUI Integration and End-to-End Test for Candle."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QRectF
from candle.ui.main_window import MainWindow
from candle.config import DeviceState, GCodeItemState


class TestGuiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication for GUI tests
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_main_window_lifecycle_and_file_loading(self):
        window = MainWindow()

        # Load sample.nc
        sample_path = os.path.join(os.path.dirname(__file__), "sample.nc")
        self.assertTrue(os.path.exists(sample_path))

        window.loadFile(sample_path)

        # Check table model
        self.assertGreater(window.m_programModel.rowCount(), 15)

        # Check parser segments
        segments = window.m_viewParser.getLineSegments()
        self.assertGreater(len(segments), 15)

        # Check bounds
        bounds_min = window.m_viewParser.getModelLowerBounds()
        bounds_max = window.m_viewParser.getModelUpperBounds()

        self.assertAlmostEqual(bounds_min.x(), 0.0, places=2)
        self.assertAlmostEqual(bounds_min.y(), 0.0, places=2)
        self.assertAlmostEqual(bounds_min.z(), -1.0, places=2)

        self.assertAlmostEqual(bounds_max.x(), 75.0, places=2)
        self.assertAlmostEqual(bounds_max.y(), 75.0, places=2)
        self.assertAlmostEqual(bounds_max.z(), 5.0, places=2)

        # Check status parser
        window._parse_status_report("<Idle|MPos:10.500,20.250,-5.000|FS:500,8000|WCO:0.000,0.000,0.000|Ov:100,100,100>")
        self.assertEqual(window.m_deviceState, DeviceState.Idle)
        self.assertAlmostEqual(window.m_mpos.x(), 10.5, places=3)
        self.assertAlmostEqual(window.m_mpos.y(), 20.25, places=3)
        self.assertAlmostEqual(window.m_mpos.z(), -5.0, places=3)

        # Check probe report parsing
        window.m_isProbing = True
        window.m_heightMapModel.resize(3, 3)
        window._parse_probe_report("[PRB:0.000,0.000,-0.125:1]")
        self.assertEqual(window.m_probeIndex, 1)

        window.close()


if __name__ == "__main__":
    unittest.main()

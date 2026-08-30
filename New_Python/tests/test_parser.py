"""Unit tests for G-code parser, preprocessor, and view parser."""

import os
import sys
import unittest
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtGui import QVector3D
from candle.config import Planes, SplineType
from candle.parser.gcode_preprocessor import GcodePreprocessorUtils
from candle.parser.gcode_parser import GcodeParser
from candle.parser.gcode_view_parser import GcodeViewParse


class TestGcodePreprocessor(unittest.TestCase):
    def test_comment_removal(self):
        cmd = "G1 X10 Y20 (This is a comment) Z5 ; trailing comment"
        stripped = GcodePreprocessorUtils.removeComment(cmd)
        self.assertEqual(stripped, "G1 X10 Y20  Z5")

    def test_command_splitting(self):
        cmd = "G0X10.5Y-20.3Z5.0F1000"
        words = GcodePreprocessorUtils.splitCommand(cmd)
        self.assertEqual(words, ["G0", "X10.5", "Y-20.3", "Z5.0", "F1000"])

    def test_speed_override(self):
        cmd = "G1 X100 Y50 F500"
        overridden, orig = GcodePreprocessorUtils.overrideSpeed(cmd, 150)
        self.assertEqual(orig, 500.0)
        self.assertIn("F750.0000", overridden)

    def test_decimal_truncation(self):
        cmd = "G1 X12.345678 Y87.654321"
        truncated = GcodePreprocessorUtils.truncateDecimals(2, cmd)
        self.assertEqual(truncated, "G1 X12.35 Y87.65")

    def test_arc_bdring_generation(self):
        # 90-degree CCW arc from (10, 0, 0) to (0, 10, 0) with center (0, 0, 0)
        start = QVector3D(10, 0, 0)
        end = QVector3D(0, 10, 0)
        center = QVector3D(0, 0, 0)
        points = GcodePreprocessorUtils.generatePointsAlongArcBDring(
            Planes.XY, start, end, center, False, 10.0, 0.1, 0.5, False, 1
        )
        self.assertGreater(len(points), 5)
        # Verify all points are roughly distance 10 from center
        for pt in points:
            dist = math.sqrt(pt.x()**2 + pt.y()**2)
            self.assertAlmostEqual(dist, 10.0, places=2)


class TestGcodeParser(unittest.TestCase):
    def test_modal_state_tracking(self):
        gp = GcodeParser()
        gp.reset(QVector3D(0, 0, 0), QVector3D(0, 0, 0))

        # Add G0
        p1 = gp.addCommand("G0 X10 Y20 Z5")
        self.assertIsNotNone(p1)
        self.assertEqual(gp.getCurrentPoint(), QVector3D(10, 20, 5))
        self.assertTrue(p1.isFastTraverse())

        # Modal G-code persistence: X30 Y40 should inherit G0
        p2 = gp.addCommand("X30 Y40")
        self.assertIsNotNone(p2)
        self.assertTrue(p2.isFastTraverse())
        self.assertEqual(gp.getCurrentPoint(), QVector3D(30, 40, 5))

        # G1 with F
        p3 = gp.addCommand("G1 Z-2 F250")
        self.assertIsNotNone(p3)
        self.assertFalse(p3.isFastTraverse())
        self.assertEqual(p3.speed(), 250.0)

    def test_view_parser_bounds(self):
        gp = GcodeParser()
        gp.reset(QVector3D(0, 0, 0), QVector3D(0, 0, 0))
        gp.addCommand("G0 X0 Y0 Z0")
        gp.addCommand("G1 X100 Y50 Z-10")
        gp.addCommand("G1 X-20 Y200 Z5")

        vp = GcodeViewParse()
        vp.updateFromParser(gp)

        min_bounds = vp.getModelLowerBounds()
        max_bounds = vp.getModelUpperBounds()

        self.assertAlmostEqual(min_bounds.x(), -20.0, places=3)
        self.assertAlmostEqual(min_bounds.y(), 0.0, places=3)
        self.assertAlmostEqual(min_bounds.z(), -10.0, places=3)

        self.assertAlmostEqual(max_bounds.x(), 100.0, places=3)
        self.assertAlmostEqual(max_bounds.y(), 200.0, places=3)
        self.assertAlmostEqual(max_bounds.z(), 5.0, places=3)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for motion planning and time estimation."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtGui import QVector3D
from candle.parser.line_segment import LineSegment
from candle.kinematics.time_estimator import TimeEstimator


class TestTimeEstimator(unittest.TestCase):
    def test_linear_move_time(self):
        # 100mm move at 600 mm/min -> nominal 10 seconds = 0.1667 minutes
        seg = LineSegment(QVector3D(0, 0, 0), QVector3D(100, 0, 0), 0)
        seg.setModelStart(QVector3D(0, 0, 0))
        seg.setModelEnd(QVector3D(100, 0, 0))
        seg.setSpeed(600.0)
        seg.setIndex(0)

        estimator = TimeEstimator([seg], steps=[200, 200, 200, 200], max_rates=[1000, 1000, 1000, 1000])
        minutes = estimator.calculateTime()

        self.assertGreater(minutes, 0.15)
        self.assertLess(minutes, 0.25)


if __name__ == "__main__":
    unittest.main()

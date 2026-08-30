"""Spline properties data structure for G5 and G5.1 commands."""

from typing import Optional
from PyQt6.QtGui import QVector3D
from ..config import SplineType


class SplineProperties:
    def __init__(self, spline_type: SplineType = SplineType.CubicSpline,
                 cp1: Optional[QVector3D] = None, cp2: Optional[QVector3D] = None):
        self.type: SplineType = spline_type
        self.controlPoint1: Optional[QVector3D] = cp1
        self.controlPoint2: Optional[QVector3D] = cp2  # None for quadratic (G5.1)

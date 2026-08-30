"""Arc properties data structure."""

from typing import Optional
from PyQt6.QtGui import QVector3D


class ArcProperties:
    def __init__(self, is_clockwise: bool = False, radius: float = 0.0,
                 center: Optional[QVector3D] = None, turns: int = 1):
        self.isClockwise: bool = is_clockwise
        self.radius: float = radius
        self.center: Optional[QVector3D] = center
        self.turns: int = turns

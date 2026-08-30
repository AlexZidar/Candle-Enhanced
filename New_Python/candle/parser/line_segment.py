"""LineSegment represents a 3D line segment with graphical and execution metadata."""

import math
from typing import Optional
from PyQt6.QtGui import QVector3D
from ..config import Planes


class LineSegment:
    def __init__(self, start: Optional[QVector3D] = None, end: Optional[QVector3D] = None,
                 line_index: int = -1):
        self.m_first: QVector3D = QVector3D(start) if start is not None else QVector3D()
        self.m_second: QVector3D = QVector3D(end) if end is not None else QVector3D()
        self.m_modelStart: QVector3D = QVector3D()
        self.m_modelEnd: QVector3D = QVector3D()
        self.m_axesStart: QVector3D = QVector3D()
        self.m_axesEnd: QVector3D = QVector3D()

        self.m_lineIndex: int = line_index
        self.m_index: int = -1
        self.m_vertexIndex: int = -1
        self.m_toolhead: int = 0
        self.m_speed: float = 0.0
        self.m_spindleSpeed: float = 0.0
        self.m_dwell: float = 0.0
        self.m_plane: Planes = Planes.XY

        # Flags
        self.isAbsolute: bool = True
        self.isArc: bool = False
        self.isClockwise: bool = False
        self.isDrawn: bool = False
        self.isFastTraverse: bool = False
        self.isHighlight: bool = False
        self.isMetric: bool = True
        self.isSpline: bool = False
        self.isZMovement: bool = False
        self.isInverseTimeFeed: bool = False

    def copy(self) -> 'LineSegment':
        other = LineSegment(self.m_first, self.m_second, self.m_lineIndex)
        other.m_modelStart = QVector3D(self.m_modelStart)
        other.m_modelEnd = QVector3D(self.m_modelEnd)
        other.m_axesStart = QVector3D(self.m_axesStart)
        other.m_axesEnd = QVector3D(self.m_axesEnd)
        other.m_index = self.m_index
        other.m_vertexIndex = self.m_vertexIndex
        other.m_toolhead = self.m_toolhead
        other.m_speed = self.m_speed
        other.m_spindleSpeed = self.m_spindleSpeed
        other.m_dwell = self.m_dwell
        other.m_plane = self.m_plane
        other.isAbsolute = self.isAbsolute
        other.isArc = self.isArc
        other.isClockwise = self.isClockwise
        other.isDrawn = self.isDrawn
        other.isFastTraverse = self.isFastTraverse
        other.isHighlight = self.isHighlight
        other.isMetric = self.isMetric
        other.isSpline = self.isSpline
        other.isZMovement = self.isZMovement
        other.isInverseTimeFeed = self.isInverseTimeFeed
        return other

    def getLineNumber(self) -> int:
        return self.m_lineIndex

    def setLineNumber(self, num: int) -> None:
        self.m_lineIndex = num

    def getStart(self) -> QVector3D:
        return self.m_first

    def setStart(self, v: QVector3D) -> None:
        self.m_first = QVector3D(v)

    def getEnd(self) -> QVector3D:
        return self.m_second

    def setEnd(self, v: QVector3D) -> None:
        self.m_second = QVector3D(v)

    def modelStart(self) -> QVector3D:
        return self.m_modelStart

    def setModelStart(self, v: QVector3D) -> None:
        self.m_modelStart = QVector3D(v)

    def modelEnd(self) -> QVector3D:
        return self.m_modelEnd

    def setModelEnd(self, v: QVector3D) -> None:
        self.m_modelEnd = QVector3D(v)

    def axesStart(self) -> QVector3D:
        return self.m_axesStart

    def setAxesStart(self, v: QVector3D) -> None:
        self.m_axesStart = QVector3D(v)

    def axesEnd(self) -> QVector3D:
        return self.m_axesEnd

    def setAxesEnd(self, v: QVector3D) -> None:
        self.m_axesEnd = QVector3D(v)

    def getToolhead(self) -> int:
        return self.m_toolhead

    def setToolHead(self, h: int) -> None:
        self.m_toolhead = h

    def getSpeed(self) -> float:
        return self.m_speed

    def setSpeed(self, s: float) -> None:
        self.m_speed = s

    def getSpindleSpeed(self) -> float:
        return self.m_spindleSpeed

    def setSpindleSpeed(self, s: float) -> None:
        self.m_spindleSpeed = s

    def getDwell(self) -> float:
        return self.m_dwell

    def setDwell(self, d: float) -> None:
        self.m_dwell = d

    def vertexIndex(self) -> int:
        return self.m_vertexIndex

    def setVertexIndex(self, idx: int) -> None:
        self.m_vertexIndex = idx

    def index(self) -> int:
        return self.m_index

    def setIndex(self, idx: int) -> None:
        self.m_index = idx

    def plane(self) -> Planes:
        return self.m_plane

    def setPlane(self, p: Planes) -> None:
        self.m_plane = p

    # Compatibility property helpers
    def setIsAbsolute(self, val: bool) -> None:
        self.isAbsolute = val

    def setIsArc(self, val: bool) -> None:
        self.isArc = val

    def setIsClockwise(self, val: bool) -> None:
        self.isClockwise = val

    def setIsDrawn(self, val: bool) -> None:
        self.isDrawn = val

    def setIsFastTraverse(self, val: bool) -> None:
        self.isFastTraverse = val

    def setIsHighlight(self, val: bool) -> None:
        self.isHighlight = val

    def setIsMetric(self, val: bool) -> None:
        self.isMetric = val

    def setIsSpline(self, val: bool) -> None:
        self.isSpline = val

    def setIsZMovement(self, val: bool) -> None:
        self.isZMovement = val

    def setIsInverseTimeFeed(self, val: bool) -> None:
        self.isInverseTimeFeed = val

    def contains(self, point: QVector3D) -> bool:
        """Check if point lies on the line segment within tolerance."""
        line = self.m_second - self.m_first
        pt = point - self.m_first
        line_len = line.length()
        pt_len = pt.length()
        sub_len = (line - pt).length()
        delta = sub_len - (line_len - pt_len)
        return delta < 0.01 and pt_len <= line_len + 0.01

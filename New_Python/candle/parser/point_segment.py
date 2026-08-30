"""PointSegment represents a discrete target point in G-code execution."""

from typing import Optional, List
import math
from PyQt6.QtGui import QVector3D
from ..config import Planes, SplineType
from .arc_properties import ArcProperties
from .spline_properties import SplineProperties


class PointSegment:
    def __init__(self, point: Optional[QVector3D] = None, axes: Optional[QVector3D] = None,
                 line_number: int = -1, center: Optional[QVector3D] = None,
                 radius: float = 0.0, clockwise: bool = False):
        self._point: QVector3D = QVector3D(point) if point is not None else QVector3D(float('nan'), float('nan'), float('nan'))
        self._axes: QVector3D = QVector3D(axes) if axes is not None else QVector3D(float('nan'), float('nan'), float('nan'))
        self._lineNumber: int = line_number
        self._toolhead: int = 0
        self._speed: float = 0.0
        self._spindleSpeed: float = 0.0
        self._dwell: float = 0.0
        self._isMetric: bool = True
        self._isZMovement: bool = False
        self._isArc: bool = False
        self._isSpline: bool = False
        self._isFastTraverse: bool = False
        self._isAbsolute: bool = True
        self._isInverseTimeFeed: bool = False
        self._plane: Planes = Planes.XY
        self._arcProperties: Optional[ArcProperties] = None
        self._splineProperties: Optional[SplineProperties] = None

        if center is not None or radius != 0.0:
            self._isArc = True
            self._arcProperties = ArcProperties(
                is_clockwise=clockwise,
                radius=radius,
                center=QVector3D(center) if center is not None else None
            )

    def point(self) -> QVector3D:
        return self._point

    def setPoint(self, p: QVector3D) -> None:
        self._point = QVector3D(p)

    def axes(self) -> QVector3D:
        return self._axes

    def setAxes(self, a: QVector3D) -> None:
        self._axes = QVector3D(a)

    def points(self) -> List[float]:
        return [self._point.x(), self._point.y(), self._point.z()]

    def toolhead(self) -> int:
        return self._toolhead

    def setToolHead(self, h: int) -> None:
        self._toolhead = h

    def lineNumber(self) -> int:
        return self._lineNumber

    def setLineNumber(self, num: int) -> None:
        self._lineNumber = num

    def speed(self) -> float:
        return self._speed

    def setSpeed(self, s: float) -> None:
        self._speed = s

    def isZMovement(self) -> bool:
        return self._isZMovement

    def setIsZMovement(self, is_z: bool) -> None:
        self._isZMovement = is_z

    def isMetric(self) -> bool:
        return self._isMetric

    def setIsMetric(self, is_m: bool) -> None:
        self._isMetric = is_m

    def isArc(self) -> bool:
        return self._isArc

    def setIsArc(self, is_a: bool) -> None:
        self._isArc = is_a

    def isFastTraverse(self) -> bool:
        return self._isFastTraverse

    def setIsFastTraverse(self, is_f: bool) -> None:
        self._isFastTraverse = is_f

    def isAbsolute(self) -> bool:
        return self._isAbsolute

    def setIsAbsolute(self, is_abs: bool) -> None:
        self._isAbsolute = is_abs

    def isInverseTimeFeed(self) -> bool:
        return self._isInverseTimeFeed

    def setIsInverseTimeFeed(self, is_inv: bool) -> None:
        self._isInverseTimeFeed = is_inv

    def plane(self) -> Planes:
        return self._plane

    def setPlane(self, p: Planes) -> None:
        self._plane = p

    def spindleSpeed(self) -> float:
        return self._spindleSpeed

    def setSpindleSpeed(self, s: float) -> None:
        self._spindleSpeed = s

    def dwell(self) -> float:
        return self._dwell

    def setDwell(self, d: float) -> None:
        self._dwell = d

    # Arc methods
    def arcProperties(self) -> Optional[ArcProperties]:
        return self._arcProperties

    def setArcCenter(self, center: Optional[QVector3D]) -> None:
        if self._arcProperties is None:
            self._arcProperties = ArcProperties()
        self._arcProperties.center = QVector3D(center) if center is not None else None

    def center(self) -> Optional[QVector3D]:
        return self._arcProperties.center if self._arcProperties else None

    def centerPoints(self) -> List[float]:
        if self._arcProperties and self._arcProperties.center:
            c = self._arcProperties.center
            return [c.x(), c.y(), c.z()]
        return []

    def isClockwise(self) -> bool:
        return self._arcProperties.isClockwise if self._arcProperties else False

    def setIsClockwise(self, cw: bool) -> None:
        if self._arcProperties is None:
            self._arcProperties = ArcProperties()
        self._arcProperties.isClockwise = cw

    def radius(self) -> float:
        return self._arcProperties.radius if self._arcProperties else 0.0

    def setRadius(self, rad: float) -> None:
        if self._arcProperties is None:
            self._arcProperties = ArcProperties()
        self._arcProperties.radius = rad

    def arcTurns(self) -> int:
        return self._arcProperties.turns if self._arcProperties else 1

    def setArcTurns(self, turns: int) -> None:
        if self._arcProperties is None:
            self._arcProperties = ArcProperties()
        self._arcProperties.turns = turns

    # Spline methods
    def isSpline(self) -> bool:
        return self._isSpline

    def setIsSpline(self, is_s: bool) -> None:
        self._isSpline = is_s

    def splineProperties(self) -> Optional[SplineProperties]:
        return self._splineProperties

    def setSplineControlPoints(self, cp1: Optional[QVector3D], cp2: Optional[QVector3D]) -> None:
        if self._splineProperties is None:
            self._splineProperties = SplineProperties()
        self._splineProperties.controlPoint1 = QVector3D(cp1) if cp1 is not None else None
        self._splineProperties.controlPoint2 = QVector3D(cp2) if cp2 is not None else None

    def splineControlPoint1(self) -> Optional[QVector3D]:
        return self._splineProperties.controlPoint1 if self._splineProperties else None

    def splineControlPoint2(self) -> Optional[QVector3D]:
        return self._splineProperties.controlPoint2 if self._splineProperties else None

    def splineType(self) -> SplineType:
        return self._splineProperties.type if self._splineProperties else SplineType.CubicSpline

    def setSplineType(self, t: SplineType) -> None:
        if self._splineProperties is None:
            self._splineProperties = SplineProperties()
        self._splineProperties.type = t

    def convertToMetric(self) -> None:
        if not self._isMetric:
            self._point = self._point * 25.4
            if self._arcProperties:
                self._arcProperties.radius *= 25.4
                if self._arcProperties.center:
                    self._arcProperties.center = self._arcProperties.center * 25.4
            if self._splineProperties:
                if self._splineProperties.controlPoint1:
                    self._splineProperties.controlPoint1 = self._splineProperties.controlPoint1 * 25.4
                if self._splineProperties.controlPoint2:
                    self._splineProperties.controlPoint2 = self._splineProperties.controlPoint2 * 25.4
            self._isMetric = True

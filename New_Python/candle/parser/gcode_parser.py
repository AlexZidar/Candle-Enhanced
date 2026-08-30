"""Modal state machine G-code parser for Candle."""

import math
from typing import List, Optional
from PyQt6.QtGui import QVector3D, QMatrix4x4
from ..config import Planes, SplineType
from .point_segment import PointSegment
from .gcode_preprocessor import GcodePreprocessorUtils


class GcodeParser:
    def __init__(self):
        self.m_isMetric: bool = True
        self.m_inAbsoluteMode: bool = True
        self.m_inAbsoluteIJKMode: bool = False
        self.m_isInverseTimeFeed: bool = False
        self.m_lastGcodeCommand: float = -1.0
        self.m_commandNumber: int = 0
        self.m_currentPlane: Planes = Planes.XY

        self.m_speedOverride: float = -1.0
        self.m_truncateDecimalLength: int = 40
        self.m_removeAllWhitespace: bool = True
        self.m_convertArcsToLines: bool = False
        self.m_smallArcThreshold: float = 1.0
        self.m_smallArcSegmentLength: float = 0.3
        self.m_lastSpeed: float = 0.0
        self.m_lastSpindleSpeed: float = 0.0
        self.m_traverseSpeed: float = 300.0
        self.m_lastSplinePQ: Optional[QVector3D] = None

        self.m_currentPoint: QVector3D = QVector3D()
        self.m_currentAxes: QVector3D = QVector3D()
        self.m_points: List[PointSegment] = []

        self.reset()

    def reset(self, initial_point: Optional[QVector3D] = None, initial_axes: Optional[QVector3D] = None) -> None:
        self.m_points.clear()
        self.m_currentPoint = QVector3D(initial_point) if initial_point is not None else QVector3D(float('nan'), float('nan'), float('nan'))
        self.m_currentAxes = QVector3D(initial_axes) if initial_axes is not None else QVector3D(float('nan'), float('nan'), float('nan'))
        self.m_currentPlane = Planes.XY
        self.m_commandNumber = 0
        self.m_lastSplinePQ = None

        # Start with initial point
        self.m_points.append(PointSegment(self.m_currentPoint, self.m_currentAxes, -1))

    def setTraverseSpeed(self, speed: float) -> None:
        self.m_traverseSpeed = speed

    def getTraverseSpeed(self) -> float:
        return self.m_traverseSpeed

    def getPointSegmentList(self) -> List[PointSegment]:
        return self.m_points

    def getCommandNumber(self) -> int:
        return self.m_commandNumber - 1

    def getCurrentPoint(self) -> QVector3D:
        return self.m_currentPoint

    def addCommand(self, command_or_args) -> Optional[PointSegment]:
        if isinstance(command_or_args, str):
            stripped = GcodePreprocessorUtils.removeComment(command_or_args)
            args = GcodePreprocessorUtils.splitCommand(stripped)
        else:
            args = command_or_args

        if not args:
            return None

        return self.processCommand(args)

    def processCommand(self, args: List[str]) -> Optional[PointSegment]:
        movement_g_codes = [0.0, 1.0, 2.0, 3.0, 5.0, 5.1, 38.2]
        ps: Optional[PointSegment] = None

        # Handle F code
        speed = GcodePreprocessorUtils.parseCoord(args, 'F')
        if not math.isnan(speed):
            self.m_lastSpeed = speed if self.m_isMetric else speed * 25.4

        # Handle S code
        spindle_speed = GcodePreprocessorUtils.parseCoord(args, 'S')
        if not math.isnan(spindle_speed):
            self.m_lastSpindleSpeed = spindle_speed

        # Handle G codes
        g_codes = GcodePreprocessorUtils.parseCodes(args, 'G')

        contains_movement = any(code in g_codes for code in movement_g_codes)
        if not contains_movement and self.m_lastGcodeCommand in movement_g_codes:
            g_codes.append(self.m_lastGcodeCommand)

        for code in g_codes:
            ps = self.handleGCode(code, args)

        return ps

    def handleGCode(self, code: float, args: List[str]) -> Optional[PointSegment]:
        ps: Optional[PointSegment] = None
        next_point = GcodePreprocessorUtils.updatePointWithCommand(args, self.m_currentPoint, self.m_inAbsoluteMode)
        next_axes = GcodePreprocessorUtils.updateAxesWithCommand(args, self.m_currentAxes, self.m_inAbsoluteMode)

        if code == 0.0:
            ps = self.addLinearPointSegment(next_point, next_axes, True)
        elif code == 1.0 or code == 38.2:
            ps = self.addLinearPointSegment(next_point, next_axes, False)
        elif code == 2.0:
            ps = self.addArcPointSegment(next_point, next_axes, True, args)
        elif code == 3.0:
            ps = self.addArcPointSegment(next_point, next_axes, False, args)
        elif code == 5.0:
            ps = self.addSplinePointSegment(next_point, next_axes, SplineType.CubicSpline, args)
        elif code == 5.1:
            ps = self.addSplinePointSegment(next_point, next_axes, SplineType.QuadraticSpline, args)
        elif code == 17.0:
            self.m_currentPlane = Planes.XY
        elif code == 18.0:
            self.m_currentPlane = Planes.ZX
        elif code == 19.0:
            self.m_currentPlane = Planes.YZ
        elif code == 20.0:
            self.m_isMetric = False
        elif code == 21.0:
            self.m_isMetric = True
        elif code == 90.0:
            self.m_inAbsoluteMode = True
        elif code == 90.1:
            self.m_inAbsoluteIJKMode = True
        elif code == 91.0:
            self.m_inAbsoluteMode = False
        elif code == 91.1:
            self.m_inAbsoluteIJKMode = False
        elif code == 93.0:
            self.m_isInverseTimeFeed = True
        elif code == 94.0:
            self.m_isInverseTimeFeed = False

        if code in (0.0, 1.0, 2.0, 3.0, 5.0, 5.1, 38.2):
            self.m_lastGcodeCommand = code

        return ps

    def addLinearPointSegment(self, next_point: QVector3D, next_axes: QVector3D, fast_traverse: bool) -> PointSegment:
        ps = PointSegment(next_point, next_axes, self.m_commandNumber)
        self.m_commandNumber += 1

        z_only = False
        cur_nan = math.isnan(self.m_currentPoint.x())
        if not cur_nan:
            if (self.m_currentAxes == next_axes or (math.isnan(self.m_currentAxes.x()) and math.isnan(next_axes.x()))) and \
               (self.m_currentPoint.x() == next_point.x()) and \
               (self.m_currentPoint.y() == next_point.y()) and \
               (self.m_currentPoint.z() != next_point.z()):
                z_only = True

        ps.setIsMetric(self.m_isMetric)
        ps.setIsZMovement(z_only)
        ps.setIsFastTraverse(fast_traverse)
        ps.setIsAbsolute(self.m_inAbsoluteMode)
        ps.setIsInverseTimeFeed(self.m_isInverseTimeFeed)
        ps.setSpeed(self.m_traverseSpeed if fast_traverse else self.m_lastSpeed)
        ps.setSpindleSpeed(self.m_lastSpindleSpeed)
        self.m_points.append(ps)

        self.m_currentPoint = QVector3D(next_point)
        self.m_currentAxes = QVector3D(next_axes)
        return ps

    def addArcPointSegment(self, next_point: QVector3D, next_axes: QVector3D,
                           clockwise: bool, args: List[str]) -> PointSegment:
        ps = PointSegment(next_point, next_axes, self.m_commandNumber)
        self.m_commandNumber += 1

        center = GcodePreprocessorUtils.updateCenterWithCommand(
            args, self.m_currentPoint, next_point, self.m_inAbsoluteIJKMode, clockwise
        )
        radius = GcodePreprocessorUtils.parseCoord(args, 'R')
        p_val = GcodePreprocessorUtils.parseCoord(args, 'P')

        if math.isnan(radius):
            m = QMatrix4x4()
            m.setToIdentity()
            if self.m_currentPlane == Planes.ZX:
                m.rotate(90, 1.0, 0.0, 0.0)
            elif self.m_currentPlane == Planes.YZ:
                m.rotate(-90, 0.0, 1.0, 0.0)

            cur_rot = m.map(self.m_currentPoint)
            cnt_rot = m.map(center)
            radius = math.sqrt((cur_rot.x() - cnt_rot.x()) ** 2 + (cur_rot.y() - cnt_rot.y()) ** 2)

        ps.setIsMetric(self.m_isMetric)
        ps.setArcCenter(center)
        ps.setIsArc(True)
        ps.setRadius(radius)
        ps.setIsClockwise(clockwise)
        ps.setIsAbsolute(self.m_inAbsoluteMode)
        ps.setIsInverseTimeFeed(self.m_isInverseTimeFeed)
        ps.setSpeed(self.m_lastSpeed)
        ps.setSpindleSpeed(self.m_lastSpindleSpeed)
        ps.setPlane(self.m_currentPlane)
        if not math.isnan(p_val):
            ps.setArcTurns(int(p_val))

        self.m_points.append(ps)
        self.m_currentPoint = QVector3D(next_point)
        return ps

    def addSplinePointSegment(self, next_point: QVector3D, next_axes: QVector3D,
                              spline_type: SplineType, args: List[str]) -> PointSegment:
        ps = PointSegment(next_point, next_axes, self.m_commandNumber)
        self.m_commandNumber += 1

        I = GcodePreprocessorUtils.parseCoord(args, 'I')
        J = GcodePreprocessorUtils.parseCoord(args, 'J')
        P = GcodePreprocessorUtils.parseCoord(args, 'P')
        Q = GcodePreprocessorUtils.parseCoord(args, 'Q')

        if spline_type == SplineType.CubicSpline:
            if math.isnan(I) and math.isnan(J):
                if self.m_lastSplinePQ is None:
                    cp1 = QVector3D(self.m_currentPoint)
                else:
                    cp1 = self.m_currentPoint + QVector3D(-self.m_lastSplinePQ.x(), -self.m_lastSplinePQ.y(), 0)
            else:
                cp1 = self.m_currentPoint + QVector3D(0 if math.isnan(I) else I, 0 if math.isnan(J) else J, 0)

            cp2 = next_point + QVector3D(0 if math.isnan(P) else P, 0 if math.isnan(Q) else Q, 0)
            ps.setSplineControlPoints(cp1, cp2)
            self.m_lastSplinePQ = QVector3D(0 if math.isnan(P) else P, 0 if math.isnan(Q) else Q, 0)
        else:
            cp1 = self.m_currentPoint + QVector3D(0 if math.isnan(I) else I, 0 if math.isnan(J) else J, 0)
            ps.setSplineControlPoints(cp1, None)

        ps.setIsSpline(True)
        ps.setSplineType(spline_type)
        ps.setIsMetric(self.m_isMetric)
        ps.setIsAbsolute(self.m_inAbsoluteMode)
        ps.setIsInverseTimeFeed(self.m_isInverseTimeFeed)
        ps.setSpeed(self.m_lastSpeed)
        ps.setSpindleSpeed(self.m_lastSpindleSpeed)
        ps.setPlane(self.m_currentPlane)

        self.m_points.append(ps)
        self.m_currentPoint = QVector3D(next_point)
        return ps

    def expandArc(self) -> List[PointSegment]:
        if len(self.m_points) < 2:
            return []

        start_segment = self.m_points[-2]
        last_segment = self.m_points[-1]

        if not last_segment.isArc():
            return []

        start = start_segment.point()
        end = last_segment.point()
        center = last_segment.center()
        radius = last_segment.radius()
        clockwise = last_segment.isClockwise()
        plane = start_segment.plane()

        if center is None:
            return []

        expanded_points = GcodePreprocessorUtils.generatePointsAlongArcBDring(
            plane, start, end, center, clockwise, radius,
            self.m_smallArcThreshold, self.m_smallArcSegmentLength, False, last_segment.arcTurns()
        )

        if not expanded_points:
            return []

        self.m_points.pop()
        self.m_commandNumber -= 1

        psl: List[PointSegment] = []
        for pt in expanded_points[1:]:
            temp = PointSegment(pt, QVector3D(), self.m_commandNumber)
            self.m_commandNumber += 1
            temp.setIsMetric(last_segment.isMetric())
            self.m_points.append(temp)
            psl.append(temp)

        if self.m_points:
            self.m_currentPoint = QVector3D(self.m_points[-1].point())

        return psl

    def preprocessCommands(self, commands: List[str]) -> List[str]:
        result = []
        for cmd in commands:
            result.extend(self.preprocessCommand(cmd))
        return result

    def preprocessCommand(self, command: str) -> List[str]:
        result: List[str] = []
        new_command = GcodePreprocessorUtils.removeComment(command)
        raw_command = new_command
        has_comment = (len(new_command) != len(command))

        if self.m_removeAllWhitespace:
            new_command = GcodePreprocessorUtils.removeAllWhitespace(new_command)

        if len(new_command) > 0:
            if self.m_speedOverride > 0:
                new_command, _ = GcodePreprocessorUtils.overrideSpeed(new_command, self.m_speedOverride)

            if self.m_truncateDecimalLength > 0:
                new_command = GcodePreprocessorUtils.truncateDecimals(self.m_truncateDecimalLength, new_command)

            if self.m_convertArcsToLines:
                arc_lines = self.convertArcsToLines(new_command)
                if arc_lines:
                    result.extend(arc_lines)
                else:
                    result.append(new_command)
            elif has_comment:
                result.append(command.replace(raw_command, new_command))
            else:
                result.append(new_command)
        elif has_comment:
            result.append(command)

        return result

    def convertArcsToLines(self, command: str) -> List[str]:
        result: List[str] = []
        start = QVector3D(self.m_currentPoint)
        ps = self.addCommand(command)

        if ps is None or not ps.isArc():
            return result

        psl = self.expandArc()
        if not psl:
            return result

        for segment in psl:
            end = segment.point()
            result.append(GcodePreprocessorUtils.generateG1FromPoints(
                start, end, self.m_inAbsoluteMode, self.m_truncateDecimalLength
            ))
            start = QVector3D(end)

        return result

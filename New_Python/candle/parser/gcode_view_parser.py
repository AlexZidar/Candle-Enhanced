"""Converts parsed PointSegments into graphical LineSegments with bounds & transformations."""

import math
from typing import List, Dict, Optional, Callable
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QVector3D, QMatrix4x4
from ..config import RotationAxis, Planes
from .point_segment import PointSegment
from .line_segment import LineSegment
from .gcode_parser import GcodeParser
from .gcode_preprocessor import GcodePreprocessorUtils


def _n_min(v1: float, v2: float) -> float:
    if not math.isnan(v1) and not math.isnan(v2):
        return min(v1, v2)
    elif not math.isnan(v1):
        return v1
    elif not math.isnan(v2):
        return v2
    return float('nan')


def _n_max(v1: float, v2: float) -> float:
    if not math.isnan(v1) and not math.isnan(v2):
        return max(v1, v2)
    elif not math.isnan(v1):
        return v1
    elif not math.isnan(v2):
        return v2
    return float('nan')


def _vec_n_min(v1: QVector3D, v2: QVector3D) -> QVector3D:
    return QVector3D(_n_min(v1.x(), v2.x()), _n_min(v1.y(), v2.y()), _n_min(v1.z(), v2.z()))


def _vec_n_max(v1: QVector3D, v2: QVector3D) -> QVector3D:
    return QVector3D(_n_max(v1.x(), v2.x()), _n_max(v1.y(), v2.y()), _n_max(v1.z(), v2.z()))


def _n_vector() -> QVector3D:
    return QVector3D(float('nan'), float('nan'), float('nan'))


def _n_assign_val(val: float, def_val: float = 0.0) -> float:
    return def_val if math.isnan(val) else val


def _n_assign(v: QVector3D, def_v: Optional[QVector3D] = None) -> QVector3D:
    d = def_v if def_v is not None else QVector3D(0, 0, 0)
    return QVector3D(
        d.x() if math.isnan(v.x()) else v.x(),
        d.y() if math.isnan(v.y()) else v.y(),
        d.z() if math.isnan(v.z()) else v.z()
    )


class GcodeViewParse:
    def __init__(self):
        self.m_lineSegments: List[LineSegment] = []
        self.m_lineSegmentIndexes: List[List[int]] = []

        self.m_axesRotationVectors: Dict[RotationAxis, QVector3D] = {
            RotationAxis.RotationAxisA: QVector3D(1.0, 0.0, 0.0),
            RotationAxis.RotationAxisB: QVector3D(1.0, 0.0, 0.0),
            RotationAxis.RotationAxisC: QVector3D(1.0, 0.0, 0.0),
        }

        self.m_viewLowerBounds: QVector3D = _n_vector()
        self.m_viewUpperBounds: QVector3D = _n_vector()
        self.m_modelLowerBounds: QVector3D = _n_vector()
        self.m_modelUpperBounds: QVector3D = _n_vector()
        self.m_modelMinLineLength: float = float('nan')

    def reset(self) -> None:
        self.m_lineSegments.clear()
        self.m_lineSegmentIndexes.clear()
        self.m_viewLowerBounds = _n_vector()
        self.m_viewUpperBounds = _n_vector()
        self.m_modelLowerBounds = _n_vector()
        self.m_modelUpperBounds = _n_vector()
        self.m_modelMinLineLength = float('nan')

    def getViewLowerBounds(self) -> QVector3D:
        return self.m_viewLowerBounds

    def getViewUpperBounds(self) -> QVector3D:
        return self.m_viewUpperBounds

    def getModelLowerBounds(self) -> QVector3D:
        return self.m_modelLowerBounds

    def getModelUpperBounds(self) -> QVector3D:
        return self.m_modelUpperBounds

    def getModelMinLineLength(self) -> float:
        return self.m_modelMinLineLength

    def getModelResolution(self) -> QSize:
        if math.isnan(self.m_modelMinLineLength) or self.m_modelMinLineLength == 0:
            return QSize(1, 1)
        w = int(((self.m_modelUpperBounds.x() - self.m_modelLowerBounds.x()) / self.m_modelMinLineLength) + 1)
        h = int(((self.m_modelUpperBounds.y() - self.m_modelLowerBounds.y()) / self.m_modelMinLineLength) + 1)
        return QSize(max(1, w), max(1, h))

    def setAxisRotationVector(self, axis: RotationAxis, vector: QVector3D) -> None:
        self.m_axesRotationVectors[axis] = QVector3D(vector)

    def getAxisRotationVector(self, axis: RotationAxis) -> QVector3D:
        return self.m_axesRotationVectors.get(axis, QVector3D(1.0, 0.0, 0.0))

    def axisRotationUsed(self, axis: RotationAxis) -> bool:
        if self.m_lineSegments:
            last = self.m_lineSegments[-1]
            if axis == RotationAxis.RotationAxisA and not math.isnan(last.axesEnd().x()):
                return True
            elif axis == RotationAxis.RotationAxisB and not math.isnan(last.axesEnd().y()):
                return True
            elif axis == RotationAxis.RotationAxisC and not math.isnan(last.axesEnd().z()):
                return True
        return False

    def getLineSegments(self) -> List[LineSegment]:
        return self.m_lineSegments

    def getLineSegmentIndexes(self) -> List[List[int]]:
        return self.m_lineSegmentIndexes

    def updateViewBounds(self, point: QVector3D) -> None:
        self.m_viewLowerBounds = _vec_n_min(self.m_viewLowerBounds, point)
        self.m_viewUpperBounds = _vec_n_max(self.m_viewUpperBounds, point)

    def updateModelBounds(self, point: QVector3D) -> None:
        self.m_modelLowerBounds = _vec_n_min(self.m_modelLowerBounds, point)
        self.m_modelUpperBounds = _vec_n_max(self.m_modelUpperBounds, point)

    def updateModelMinLineLength(self, start: QVector3D, end: QVector3D) -> None:
        length = (start - end).length()
        if not math.isnan(length) and length != 0:
            self.m_modelMinLineLength = length if math.isnan(self.m_modelMinLineLength) else min(self.m_modelMinLineLength, length)

    def updateFromParser(self, gp: GcodeParser, arc_precision: float = 0.3,
                         arc_degree_mode: bool = False,
                         is_cancelled: Optional[Callable[[], bool]] = None) -> None:
        psl = gp.getPointSegmentList()
        min_arc_length = 0.1
        rotation_delta = 5.0

        start: Optional[QVector3D] = None
        start_axes: Optional[QVector3D] = None
        start_rotation = QMatrix4x4()
        start_rotation.setToIdentity()
        end_rotation = QMatrix4x4()
        end_rotation.setToIdentity()

        index = 0
        line_index = 0

        self.m_lineSegmentIndexes = [[] for _ in range(len(psl))]

        for ps in psl:
            is_metric = ps.isMetric()
            ps.convertToMetric()

            end = ps.point()
            end_axes = ps.axes()

            if start is not None:
                if ps.isArc():
                    points = GcodePreprocessorUtils.generatePointsAlongArcBDring(
                        ps.plane(), start, end,
                        ps.center() or QVector3D(), ps.isClockwise(), ps.radius(),
                        min_arc_length, arc_precision, arc_degree_mode, ps.arcTurns()
                    )
                    segments_count = len(points)
                    if segments_count > 0:
                        rotation = _n_assign_val(start_axes.x()) - _n_assign_val(end_axes.x())
                        segment_rotation = rotation / segments_count

                        start_point = QVector3D(start)
                        for next_point in points:
                            if next_point == start_point:
                                continue
                            rot_vec = self.m_axesRotationVectors.get(RotationAxis.RotationAxisA)
                            if rot_vec and not math.isnan(rot_vec.x()):
                                end_rotation.rotate(segment_rotation, rot_vec)

                            ls = LineSegment(start_rotation.map(start_point), end_rotation.map(next_point), line_index)
                            ls.setIsArc(ps.isArc())
                            ls.setIsClockwise(ps.isClockwise())
                            ls.setPlane(ps.plane())
                            ls.setIsFastTraverse(ps.isFastTraverse())
                            ls.setIsZMovement(ps.isZMovement())
                            ls.setIsMetric(is_metric)
                            ls.setIsAbsolute(ps.isAbsolute())
                            ls.setIsInverseTimeFeed(ps.isInverseTimeFeed())
                            ls.setSpeed(ps.speed())
                            ls.setSpindleSpeed(ps.spindleSpeed())
                            ls.setDwell(ps.dwell())
                            ls.setModelStart(start_point)
                            ls.setModelEnd(next_point)
                            ls.setAxesStart(start_axes)
                            ls.setAxesEnd(end_axes)
                            ls.setIndex(index)
                            index += 1

                            self.updateViewBounds(ls.getEnd())
                            self.updateModelBounds(next_point)

                            self.m_lineSegments.append(ls)
                            if ps.lineNumber() >= 0 and ps.lineNumber() < len(self.m_lineSegmentIndexes):
                                self.m_lineSegmentIndexes[ps.lineNumber()].append(len(self.m_lineSegments) - 1)

                            start_point = QVector3D(next_point)
                            start_rotation = QMatrix4x4(end_rotation)
                        line_index += 1

                elif ps.isSpline():
                    points = GcodePreprocessorUtils.generatePointsAlongSpline(
                        start, end, ps.splineControlPoint1(), ps.splineControlPoint2()
                    )
                    segments_count = len(points)
                    if segments_count > 0:
                        rotation = _n_assign_val(start_axes.x()) - _n_assign_val(end_axes.x())
                        segment_rotation = rotation / segments_count

                        start_point = QVector3D(start)
                        for next_point in points:
                            rot_vec = self.m_axesRotationVectors.get(RotationAxis.RotationAxisA)
                            if rot_vec and not math.isnan(rot_vec.x()):
                                end_rotation.rotate(segment_rotation, rot_vec)

                            ls = LineSegment(start_rotation.map(start_point), end_rotation.map(next_point), line_index)
                            ls.setIsSpline(True)
                            ls.setIsFastTraverse(ps.isFastTraverse())
                            ls.setIsZMovement(ps.isZMovement())
                            ls.setIsMetric(is_metric)
                            ls.setIsAbsolute(ps.isAbsolute())
                            ls.setIsInverseTimeFeed(ps.isInverseTimeFeed())
                            ls.setSpeed(ps.speed())
                            ls.setSpindleSpeed(ps.spindleSpeed())
                            ls.setDwell(ps.dwell())
                            ls.setModelStart(start_point)
                            ls.setModelEnd(next_point)
                            ls.setAxesStart(start_axes)
                            ls.setAxesEnd(end_axes)
                            ls.setIndex(index)
                            index += 1

                            self.updateViewBounds(ls.getEnd())
                            self.updateModelBounds(next_point)

                            self.m_lineSegments.append(ls)
                            if ps.lineNumber() >= 0 and ps.lineNumber() < len(self.m_lineSegmentIndexes):
                                self.m_lineSegmentIndexes[ps.lineNumber()].append(len(self.m_lineSegments) - 1)

                            start_point = QVector3D(next_point)
                            start_rotation = QMatrix4x4(end_rotation)
                        line_index += 1

                else:
                    start_point = QVector3D(start)
                    rotation = _n_assign_val(start_axes.x()) - _n_assign_val(end_axes.x())
                    segments = max(int(abs(rotation) / rotation_delta), 1)
                    segment_vector = (end - start_point) / segments
                    segment_rotation = rotation / segments

                    for i in range(segments):
                        next_point = start_point + segment_vector if segments > 1 else QVector3D(end)
                        rot_vec = self.m_axesRotationVectors.get(RotationAxis.RotationAxisA)
                        if rot_vec and not math.isnan(rot_vec.x()):
                            end_rotation.rotate(segment_rotation, rot_vec)

                        ls = LineSegment(start_rotation.map(start_point), end_rotation.map(next_point), line_index)
                        ls.setIsArc(ps.isArc())
                        ls.setIsFastTraverse(ps.isFastTraverse())
                        ls.setIsZMovement(ps.isZMovement())
                        ls.setIsMetric(is_metric)
                        ls.setIsAbsolute(ps.isAbsolute())
                        ls.setIsInverseTimeFeed(ps.isInverseTimeFeed())
                        ls.setSpeed(ps.speed())
                        ls.setSpindleSpeed(ps.spindleSpeed())
                        ls.setDwell(ps.dwell())
                        ls.setModelStart(start_point)
                        ls.setModelEnd(next_point)
                        ls.setAxesStart(start_axes)
                        ls.setAxesEnd(end_axes)
                        ls.setIndex(index)

                        self.updateViewBounds(ls.getEnd())
                        self.updateModelBounds(next_point)
                        self.updateModelMinLineLength(start_point, next_point)

                        self.m_lineSegments.append(ls)
                        if ps.lineNumber() >= 0 and ps.lineNumber() < len(self.m_lineSegmentIndexes):
                            self.m_lineSegmentIndexes[ps.lineNumber()].append(len(self.m_lineSegments) - 1)

                        start_point = QVector3D(next_point)
                        start_rotation = QMatrix4x4(end_rotation)

                    line_index += 1
                    index += 1

            start = QVector3D(end)
            start_axes = QVector3D(end_axes)

            if is_cancelled and is_cancelled():
                return

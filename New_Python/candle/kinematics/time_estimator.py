"""Kinematic planner simulation and job time estimation for GRBL."""

import math
from typing import List, Optional, Callable, Dict
from PyQt6.QtGui import QVector4D, QVector3D
from ..parser.line_segment import LineSegment


class TimeEstimator:
    def __init__(self, segments: List[LineSegment], steps: Optional[List[float]] = None,
                 max_rates: Optional[List[int]] = None, accelerations: Optional[List[int]] = None,
                 feed_override: bool = False, rapid_override: bool = False,
                 feed_override_value: float = 1.0, rapid_override_value: float = 1.0,
                 laser_mode: bool = False, spindle_delay: float = 0.0,
                 junction_deviation: float = 0.01, planner_buffer_size: int = 15,
                 min_junction_velocity: float = 0.0):
        self.m_segments: List[LineSegment] = segments
        self.m_feedOverride: bool = feed_override
        self.m_rapidOverride: bool = rapid_override
        self.m_feedOverrideValue: float = feed_override_value
        self.m_rapidOverrideValue: float = rapid_override_value
        self.m_laserMode: bool = laser_mode
        self.m_spindleDelay: float = spindle_delay

        self.m_junctionDeviation: float = junction_deviation or 0.01
        self.m_plannerBufferSize: int = planner_buffer_size or 15
        self.m_minJunctionVelocity: float = min_junction_velocity or 0.0

        default_steps = [200.0, 200.0, 200.0, 200.0]
        default_max_rates = [1000, 1000, 1000, 1000]
        default_accel = [400 * 3600, 400 * 3600, 400 * 3600, 400 * 3600]

        self.m_steps: List[float] = [steps[i] if (steps and i < len(steps) and steps[i] != 0) else default_steps[i] for i in range(4)]
        self.m_maxRates: List[int] = [max_rates[i] if (max_rates and i < len(max_rates) and max_rates[i] != 0) else default_max_rates[i] for i in range(4)]
        self.m_accelerations: List[int] = [accelerations[i] if (accelerations and i < len(accelerations) and accelerations[i] != 0) else default_accel[i] for i in range(4)]

        self.m_currentTime: float = 0.0
        self.m_currentIndex: int = 0
        self.m_bufferIndex: int = 0
        self.m_currentVelocity: float = 0.0
        self.m_previousLineNumber: int = -1
        self.m_previousSpindleSpeed: float = 0.0

        self.m_cacheNominalVelocity: Dict[int, float] = {}
        self.m_cacheJunctionVelocity: Dict[int, float] = {}
        self.m_cacheAcceleration: Dict[int, float] = {}
        self.m_cacheLength: Dict[int, float] = {}
        self.m_cacheVector: Dict[int, QVector4D] = {}
        self.m_cacheRefineSegment: Dict[int, tuple] = {}
        self.m_segmentBuffer: List[LineSegment] = []

        self.reset()

    def reset(self) -> None:
        self.m_currentTime = 0.0
        self.m_currentIndex = 0
        self.m_bufferIndex = 0
        self.m_currentVelocity = 0.0
        self.m_previousLineNumber = -1
        self.m_previousSpindleSpeed = 0.0

        self.m_cacheNominalVelocity.clear()
        self.m_cacheJunctionVelocity.clear()
        self.m_cacheAcceleration.clear()
        self.m_cacheLength.clear()
        self.m_cacheVector.clear()
        self.m_cacheRefineSegment.clear()
        self.m_segmentBuffer.clear()

    def time(self) -> float:
        """Returns time estimate in minutes."""
        return self.m_currentTime

    def progress(self) -> int:
        return int(self.m_currentIndex * 100 / len(self.m_segments)) if self.m_segments else 100

    def calculateTime(self, is_cancelled: Optional[Callable[[], bool]] = None) -> float:
        self.reset()
        while self.advance():
            if is_cancelled and is_cancelled():
                break
        return self.time()

    def advance(self) -> bool:
        if not self.m_segments or self.m_currentIndex >= len(self.m_segments):
            return False

        batch_size = max(1, len(self.m_segments) // 100)
        i = self.m_currentIndex
        j = self.m_bufferIndex

        while i < (self.m_currentIndex + batch_size) and i < len(self.m_segments):
            segment = self.m_segments[i].copy()
            skip_count = self.refineSegment(i, segment)
            i += skip_count

            vector = self.getVector(segment)
            acceleration = self.getAcceleration(segment)

            # Fill planner buffer
            if not self.m_segmentBuffer:
                j = i
                self.m_segmentBuffer.append(segment)
                k = 0
                while k < (self.m_plannerBufferSize - 1) and j < len(self.m_segments):
                    next_seg = self.m_segments[j].copy()
                    j += self.refineSegment(j, next_seg)
                    self.m_segmentBuffer.append(next_seg)
                    k += 1
            else:
                if self.m_segmentBuffer:
                    self.m_segmentBuffer.pop(0)
                while len(self.m_segmentBuffer) < self.m_plannerBufferSize and j < len(self.m_segments):
                    last_seg = self.m_segments[j].copy()
                    j += self.refineSegment(j, last_seg)
                    self.m_segmentBuffer.append(last_seg)

            # Backward pass for exit velocity
            backward_entry_velocity = 0.0
            for k in range(len(self.m_segmentBuffer) - 1, 0, -1):
                seg_k = self.m_segmentBuffer[k]
                seg_prev = self.m_segmentBuffer[k - 1]
                backward_acc_vel = math.sqrt(
                    backward_entry_velocity * backward_entry_velocity
                    + 2 * self.getAcceleration(seg_k) * self.getLength(seg_k)
                )
                backward_junc_vel = self.getJunctionVelocity(seg_prev, seg_k)
                backward_nom_vel = self.getNominalVelocity(seg_k)
                backward_entry_velocity = min(backward_acc_vel, min(backward_junc_vel, backward_nom_vel))

            exit_velocity = backward_entry_velocity

            # Forward pass
            nominal_velocity = self.getNominalVelocity(segment)
            acc = acceleration if acceleration > 0 else 1.0

            t0 = abs(nominal_velocity - self.m_currentVelocity) / acc
            t2 = abs(exit_velocity - nominal_velocity) / acc
            s1 = vector.length() - (self.m_currentVelocity + nominal_velocity) / 2.0 * t0 \
                - (nominal_velocity + exit_velocity) / 2.0 * t2
            t1 = s1 / nominal_velocity if nominal_velocity > 0 else 0.0

            if t1 >= 0:
                t = t0 + t1 + t2
            else:
                if abs(exit_velocity * exit_velocity - self.m_currentVelocity * self.m_currentVelocity) / (2.0 * acc) > vector.length():
                    sign = -1.0 if exit_velocity < self.m_currentVelocity else 1.0
                    val = self.m_currentVelocity * self.m_currentVelocity + 2.0 * acc * vector.length() * sign
                    exit_velocity = math.sqrt(max(0.0, val))
                    avg_v = (exit_velocity + self.m_currentVelocity) / 2.0
                    t = vector.length() / avg_v if avg_v > 0 else 0.0
                else:
                    peak_vel = math.sqrt(max(0.0, (2.0 * acc * vector.length() + self.m_currentVelocity * self.m_currentVelocity + exit_velocity * exit_velocity) / 2.0))
                    t = (abs(peak_vel - self.m_currentVelocity) + abs(exit_velocity - peak_vel)) / acc

            # Dwell
            if segment.getDwell() != 0 and segment.getLineNumber() != self.m_previousLineNumber:
                self.m_previousLineNumber = segment.getLineNumber()
                self.m_currentTime += segment.getDwell() / 60.0

            # Spindle delay
            if not self.m_laserMode and abs(segment.getSpindleSpeed() - self.m_previousSpindleSpeed) > 1e-5:
                self.m_previousSpindleSpeed = segment.getSpindleSpeed()
                self.m_currentTime += self.m_spindleDelay / 60.0

            if not math.isnan(t) and not math.isinf(t):
                self.m_currentTime += t

            self.m_currentVelocity = exit_velocity

        self.m_currentIndex = i
        self.m_bufferIndex = j

        return self.m_currentIndex < len(self.m_segments)

    def getNominalVelocity(self, segment: LineSegment) -> float:
        if segment.index() in self.m_cacheNominalVelocity:
            return self.m_cacheNominalVelocity[segment.index()]

        result = segment.getSpeed()
        if segment.isInverseTimeFeed:
            result *= self.getVector(segment).length()
        if self.m_feedOverride and not segment.isFastTraverse:
            result *= self.m_feedOverrideValue
        elif self.m_rapidOverride and segment.isFastTraverse:
            result *= self.m_rapidOverrideValue

        unit = self.getVector(segment).normalized()
        result = min(result, self.limitByAxes(self.m_maxRates, unit))
        self.m_cacheNominalVelocity[segment.index()] = result
        return result

    def getJunctionVelocity(self, segment1: LineSegment, segment2: LineSegment) -> float:
        if segment1.index() in self.m_cacheJunctionVelocity:
            return self.m_cacheJunctionVelocity[segment1.index()]

        unit1 = self.getVector(segment1).normalized()
        unit2 = self.getVector(segment2).normalized()
        dot = unit1.x() * unit2.x() + unit1.y() * unit2.y() + unit1.z() * unit2.z() + unit1.w() * unit2.w()
        cos_theta = -dot

        if cos_theta > 0.999999:
            result = self.m_minJunctionVelocity
        elif cos_theta < -0.999999:
            result = float('inf')
        else:
            junc_unit = (unit2 - unit1).normalized()
            sin_theta2 = math.sqrt(max(0.0, 0.5 * (1.0 - cos_theta)))
            if sin_theta2 < 1.0:
                acc_limit = self.limitByAxes(self.m_accelerations, junc_unit)
                val = (acc_limit * self.m_junctionDeviation * sin_theta2) / (1.0 - sin_theta2)
                result = max(self.m_minJunctionVelocity, math.sqrt(max(0.0, val)))
            else:
                result = self.m_minJunctionVelocity

        self.m_cacheJunctionVelocity[segment1.index()] = result
        return result

    def limitByAxes(self, limits: List[int], unit: QVector4D) -> float:
        result = float('inf')
        coords = [unit.x(), unit.y(), unit.z(), unit.w()]
        for i in range(min(len(limits), 4)):
            u = abs(coords[i])
            if u > 1e-9:
                result = min(result, abs(float(limits[i]) / u))
        return result

    def getAcceleration(self, segment: LineSegment) -> float:
        if segment.index() in self.m_cacheAcceleration:
            return self.m_cacheAcceleration[segment.index()]

        unit = self.getVector(segment).normalized()
        result = self.limitByAxes(self.m_accelerations, unit)
        self.m_cacheAcceleration[segment.index()] = result
        return result

    def getLength(self, segment: LineSegment) -> float:
        if segment.index() in self.m_cacheLength:
            return self.m_cacheLength[segment.index()]

        result = self.getVector(segment).length()
        self.m_cacheLength[segment.index()] = result
        return result

    def getVector(self, segment: LineSegment) -> QVector4D:
        if segment.index() in self.m_cacheVector:
            return self.m_cacheVector[segment.index()]

        def _safe_round(val: float, step: float) -> float:
            return 0.0 if math.isnan(val) else round(val * step) / step

        sx = _safe_round(segment.modelStart().x(), self.m_steps[0])
        sy = _safe_round(segment.modelStart().y(), self.m_steps[1])
        sz = _safe_round(segment.modelStart().z(), self.m_steps[2])
        sa = _safe_round(segment.axesStart().x(), self.m_steps[3])

        ex = _safe_round(segment.modelEnd().x(), self.m_steps[0])
        ey = _safe_round(segment.modelEnd().y(), self.m_steps[1])
        ez = _safe_round(segment.modelEnd().z(), self.m_steps[2])
        ea = _safe_round(segment.axesEnd().x(), self.m_steps[3])

        result = QVector4D(ex - sx, ey - sy, ez - sz, ea - sa if not math.isnan(ea - sa) else 0.0)
        self.m_cacheVector[segment.index()] = result
        return result

    def refineSegment(self, index: int, segment: LineSegment) -> int:
        result = 1
        if segment.index() in self.m_cacheRefineSegment:
            end, model_end, axes_end, res = self.m_cacheRefineSegment[segment.index()]
            segment.setEnd(end)
            segment.setModelEnd(model_end)
            segment.setAxesEnd(axes_end)
            return res

        for i in range(index + 1, len(self.m_segments)):
            if self.m_segments[i].index() != segment.index():
                prev = self.m_segments[i - 1]
                segment.setEnd(prev.getEnd())
                segment.setModelEnd(prev.modelEnd())
                segment.setAxesEnd(prev.axesEnd())
                result = i - index
                break

        self.m_cacheRefineSegment[segment.index()] = (
            QVector3D(segment.getEnd()),
            QVector3D(segment.modelEnd()),
            QVector3D(segment.axesEnd()),
            result
        )
        return result

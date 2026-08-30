"""G-Code Preprocessor Utilities for Candle."""

import re
import math
from typing import List, Optional, Tuple
from PyQt6.QtGui import QVector3D, QMatrix4x4
from ..config import Planes


class GcodePreprocessorUtils:
    @staticmethod
    def overrideSpeed(command: str, speed: float) -> Tuple[str, Optional[float]]:
        """Searches command string for F code and replaces speed with ratio."""
        original = None
        match = re.search(r'[Ff]([0-9.]+)', command)
        if match:
            original = float(match.group(1))
            new_feed = original / 100.0 * speed
            command = command[:match.start()] + f"F{new_feed:.4f}" + command[match.end():]
        return command, original

    @staticmethod
    def removeComment(command: str) -> str:
        """Removes comments in parentheses (...) or starting with semicolon ;."""
        if '(' in command:
            command = re.sub(r'\(+[^\(]*\)+', '', command)
        if ';' in command:
            command = re.sub(r';.*', '', command)
        return command.strip()

    @staticmethod
    def parseComment(command: str) -> str:
        """Finds first comment in string."""
        match = re.search(r'(\([^\(\)]*\)|;[^;].*)', command)
        return match.group(1) if match else ""

    @staticmethod
    def truncateDecimals(length: int, command: str) -> str:
        """Truncates floating point numbers to given decimal places."""
        def repl(m):
            val = float(m.group(1))
            return f"{val:.{length}f}"
        return re.sub(r'(\d*\.\d+)', repl, command)

    @staticmethod
    def removeAllWhitespace(command: str) -> str:
        """Removes all whitespace characters."""
        return re.sub(r'\s+', '', command)

    @staticmethod
    def parseCodes(args: List[str], code: str) -> List[float]:
        """Parses all occurrences of given letter code (e.g. 'G', 'M')."""
        code_upper = code.upper()
        res = []
        for s in args:
            if s and s[0].upper() == code_upper:
                try:
                    res.append(float(s[1:]))
                except ValueError:
                    pass
        return res

    @staticmethod
    def parseGCodes(command: str) -> List[int]:
        codes = []
        for m in re.finditer(r'[Gg]0*(\d+)', command):
            codes.append(int(m.group(1)))
        return codes

    @staticmethod
    def parseMCodes(command: str) -> List[int]:
        codes = []
        for m in re.finditer(r'[Mm]0*(\d+)', command):
            codes.append(int(m.group(1)))
        return codes

    @staticmethod
    def splitCommand(command: str) -> List[str]:
        """Splits a G-code command by word/letter argument without relying on spaces."""
        l: List[str] = []
        sb: List[str] = []
        read_numeric = False

        for c in command:
            is_digit = ('0' <= c <= '9')
            is_letter = ('a' <= c <= 'z') or ('A' <= c <= 'Z')

            if read_numeric and not is_digit and c != '.':
                read_numeric = False
                if sb:
                    l.append("".join(sb))
                sb = []
                if is_letter:
                    sb.append(c)
            elif is_digit or c == '.' or c == '-':
                sb.append(c)
                read_numeric = True
            elif is_letter:
                sb.append(c)

        if sb:
            l.append("".join(sb))

        return l

    @staticmethod
    def parseCoord(args: List[str], c: str) -> float:
        """Extract coordinate value for letter c (X, Y, Z, A, B, C, I, J, K, R, P, Q, F, S)."""
        c_upper = c.upper()
        for t in args:
            if t and t[0].upper() == c_upper:
                try:
                    return float(t[1:])
                except ValueError:
                    return float('nan')
        return float('nan')

    @staticmethod
    def updatePointWithCommand(command_args_or_initial, initial_or_x=None,
                              y=None, z=None, absolute_mode: bool = True) -> QVector3D:
        if isinstance(command_args_or_initial, list):
            command_args: List[str] = command_args_or_initial
            initial: QVector3D = initial_or_x
            x_val = GcodePreprocessorUtils.parseCoord(command_args, 'X')
            y_val = GcodePreprocessorUtils.parseCoord(command_args, 'Y')
            z_val = GcodePreprocessorUtils.parseCoord(command_args, 'Z')
            return GcodePreprocessorUtils._updatePoint(initial, x_val, y_val, z_val, absolute_mode)
        else:
            initial: QVector3D = command_args_or_initial
            x_val = initial_or_x
            return GcodePreprocessorUtils._updatePoint(initial, x_val, y, z, absolute_mode)

    @staticmethod
    def _updatePoint(initial: QVector3D, x: float, y: float, z: float, absolute_mode: bool) -> QVector3D:
        new_point = QVector3D(initial)
        if absolute_mode:
            if not math.isnan(x):
                new_point.setX(x)
            if not math.isnan(y):
                new_point.setY(y)
            if not math.isnan(z):
                new_point.setZ(z)
        else:
            if not math.isnan(x):
                new_point.setX(new_point.x() + x)
            if not math.isnan(y):
                new_point.setY(new_point.y() + y)
            if not math.isnan(z):
                new_point.setZ(new_point.z() + z)
        return new_point

    @staticmethod
    def updateAxesWithCommand(command_args: List[str], initial: QVector3D, absolute_mode: bool) -> QVector3D:
        a = GcodePreprocessorUtils.parseCoord(command_args, 'A')
        b = GcodePreprocessorUtils.parseCoord(command_args, 'B')
        c = GcodePreprocessorUtils.parseCoord(command_args, 'C')
        new_axes = QVector3D(initial)
        if absolute_mode:
            if not math.isnan(a):
                new_axes.setX(a)
            if not math.isnan(b):
                new_axes.setY(b)
            if not math.isnan(c):
                new_axes.setZ(c)
        else:
            if not math.isnan(a):
                new_axes.setX(new_axes.x() + a)
            if not math.isnan(b):
                new_axes.setY(new_axes.y() + b)
            if not math.isnan(c):
                new_axes.setZ(new_axes.z() + c)
        return new_axes

    @staticmethod
    def convertRToCenter(start: QVector3D, end: QVector3D, radius: float,
                         absolute_ijk: bool, clockwise: bool) -> QVector3D:
        R = radius
        center = QVector3D()
        x = end.x() - start.x()
        y = end.y() - start.y()

        h_x2_div_d = 4 * R * R - x * x - y * y
        if h_x2_div_d < 0:
            h_x2_div_d = 0.0
        h_x2_div_d = (-math.sqrt(h_x2_div_d)) / (math.hypot(x, y) or 1e-9)

        if not clockwise:
            h_x2_div_d = -h_x2_div_d

        if R < 0:
            h_x2_div_d = -h_x2_div_d
            radius = -radius

        offset_x = 0.5 * (x - (y * h_x2_div_d))
        offset_y = 0.5 * (y + (x * h_x2_div_d))

        if not absolute_ijk:
            center.setX(start.x() + offset_x)
            center.setY(start.y() + offset_y)
        else:
            center.setX(offset_x)
            center.setY(offset_y)

        return center

    @staticmethod
    def updateCenterWithCommand(command_args: List[str], initial: QVector3D, next_point: QVector3D,
                                absolute_ijk_mode: bool, clockwise: bool) -> QVector3D:
        i = GcodePreprocessorUtils.parseCoord(command_args, 'I')
        j = GcodePreprocessorUtils.parseCoord(command_args, 'J')
        k = GcodePreprocessorUtils.parseCoord(command_args, 'K')
        r = GcodePreprocessorUtils.parseCoord(command_args, 'R')

        if math.isnan(i) and math.isnan(j) and math.isnan(k):
            return GcodePreprocessorUtils.convertRToCenter(initial, next_point, r, absolute_ijk_mode, clockwise)

        return GcodePreprocessorUtils._updatePoint(initial, i, j, k, absolute_ijk_mode)

    @staticmethod
    def generateG1FromPoints(start: QVector3D, end: QVector3D, absolute_mode: bool, precision: int) -> str:
        sb = ["G1"]
        if absolute_mode:
            if not math.isnan(end.x()):
                sb.append(f"X{end.x():.{precision}f}")
            if not math.isnan(end.y()):
                sb.append(f"Y{end.y():.{precision}f}")
            if not math.isnan(end.z()):
                sb.append(f"Z{end.z():.{precision}f}")
        else:
            if not math.isnan(end.x()):
                sb.append(f"X{(end.x() - start.x()):.{precision}f}")
            if not math.isnan(end.y()):
                sb.append(f"Y{(end.y() - start.y()):.{precision}f}")
            if not math.isnan(end.z()):
                sb.append(f"Z{(end.z() - start.z()):.{precision}f}")
        return "".join(sb)

    @staticmethod
    def getAngle(start: QVector3D, end: QVector3D) -> float:
        """Return angle in radians [0, 2pi) from start to end."""
        dx = end.x() - start.x()
        dy = end.y() - start.y()

        if dx != 0:
            if dx > 0 and dy >= 0:
                angle = math.atan(dy / dx)
            elif dx < 0 and dy >= 0:
                angle = math.pi - abs(math.atan(dy / dx))
            elif dx < 0 and dy < 0:
                angle = math.pi + abs(math.atan(dy / dx))
            else:
                angle = math.pi * 2.0 - abs(math.atan(dy / dx))
        else:
            if dy > 0:
                angle = math.pi / 2.0
            else:
                angle = math.pi * 3.0 / 2.0

        return angle

    @staticmethod
    def calculateSweep(start_angle: float, end_angle: float, is_cw: bool, turns: int = 1) -> float:
        if start_angle == end_angle:
            sweep = math.pi * 2.0
        else:
            if end_angle == 0:
                end_angle = math.pi * 2.0
            if not is_cw and end_angle < start_angle:
                sweep = ((math.pi * 2.0 - start_angle) + end_angle)
            elif is_cw and end_angle > start_angle:
                sweep = ((math.pi * 2.0 - end_angle) + start_angle)
            else:
                sweep = abs(end_angle - start_angle)

        if turns > 1:
            sweep += (math.pi * 2.0) * (turns - 1)

        return sweep

    @staticmethod
    def generatePointsAlongArcBDring(plane: Planes, start: QVector3D, end: QVector3D,
                                     center: QVector3D, clockwise: bool, R: float,
                                     min_arc_length: float, arc_precision: float,
                                     arc_degree_mode: bool, turns: int = 1) -> List[QVector3D]:
        radius = R
        m = QMatrix4x4()
        m.setToIdentity()

        if plane == Planes.ZX:
            m.rotate(90, 1.0, 0.0, 0.0)
        elif plane == Planes.YZ:
            m.rotate(-90, 0.0, 1.0, 0.0)

        s_rot = m.map(start)
        e_rot = m.map(end)
        c_rot = m.map(center)

        if math.isnan(c_rot.length()):
            return []

        if radius == 0:
            radius = math.sqrt((s_rot.x() - c_rot.x()) ** 2 + (s_rot.y() - c_rot.y()) ** 2)

        start_angle = GcodePreprocessorUtils.getAngle(c_rot, s_rot)
        end_angle = GcodePreprocessorUtils.getAngle(c_rot, e_rot)
        sweep = GcodePreprocessorUtils.calculateSweep(start_angle, end_angle, clockwise, turns)
        arc_length = sweep * radius

        if arc_degree_mode and arc_precision > 0:
            num_points = max(1, int(sweep / (math.pi * arc_precision / 180.0)))
        else:
            if arc_precision <= 0 and min_arc_length > 0:
                arc_precision = min_arc_length
            num_points = int(math.ceil(arc_length / (arc_precision or 0.1))) if arc_precision else 1
            num_points = max(1, num_points)

        # Restore matrix
        m_inv = QMatrix4x4()
        m_inv.setToIdentity()
        if plane == Planes.ZX:
            m_inv.rotate(-90, 1.0, 0.0, 0.0)
        elif plane == Planes.YZ:
            m_inv.rotate(90, 0.0, 1.0, 0.0)

        line_end = QVector3D(e_rot.x(), e_rot.y(), s_rot.z())
        segments = []
        z_increment = (e_rot.z() - s_rot.z()) / num_points

        for i in range(1, num_points):
            if clockwise:
                angle = start_angle - i * sweep / num_points
            else:
                angle = start_angle + i * sweep / num_points

            if angle >= math.pi * 2.0:
                angle -= math.pi * 2.0
            elif angle < 0:
                angle += math.pi * 2.0

            line_end.setX(math.cos(angle) * radius + c_rot.x())
            line_end.setY(math.sin(angle) * radius + c_rot.y())
            line_end.setZ(line_end.z() + z_increment)

            segments.append(m_inv.map(line_end))

        segments.append(m_inv.map(e_rot))
        return segments

    @staticmethod
    def lerp(a: QVector3D, b: QVector3D, t: float) -> QVector3D:
        return (1.0 - t) * a + t * b

    @staticmethod
    def evalCubicBSpline(t: float, p0: QVector3D, p1: QVector3D, p2: QVector3D, p3: QVector3D) -> QVector3D:
        q0 = GcodePreprocessorUtils.lerp(p0, p1, t)
        q1 = GcodePreprocessorUtils.lerp(p1, p2, t)
        q2 = GcodePreprocessorUtils.lerp(p2, p3, t)
        r0 = GcodePreprocessorUtils.lerp(q0, q1, t)
        r1 = GcodePreprocessorUtils.lerp(q1, q2, t)
        return GcodePreprocessorUtils.lerp(r0, r1, t)

    @staticmethod
    def evalQuadraticBSpline(t: float, p0: QVector3D, p1: QVector3D, p2: QVector3D) -> QVector3D:
        q0 = GcodePreprocessorUtils.lerp(p0, p1, t)
        q1 = GcodePreprocessorUtils.lerp(p1, p2, t)
        return GcodePreprocessorUtils.lerp(q0, q1, t)

    @staticmethod
    def generatePointsAlongSpline(start: QVector3D, end: QVector3D,
                                  cp1: Optional[QVector3D], cp2: Optional[QVector3D],
                                  tolerance: float = 0.1) -> List[QVector3D]:
        points: List[QVector3D] = []
        MIN_STEP = 0.001
        MAX_STEP = 0.1
        t = 0.0
        step = MAX_STEP
        is_cubic = (cp2 is not None)

        p_cp1 = cp1 if cp1 is not None else start
        p_cp2 = cp2 if cp2 is not None else end

        while t < 1.0:
            t_next = min(t + step, 1.0)
            t_mid = t + (t_next - t) / 2.0

            if is_cubic:
                curr = GcodePreprocessorUtils.evalCubicBSpline(t, start, p_cp1, p_cp2, end)
                nxt = GcodePreprocessorUtils.evalCubicBSpline(t_next, start, p_cp1, p_cp2, end)
                mid = GcodePreprocessorUtils.evalCubicBSpline(t_mid, start, p_cp1, p_cp2, end)
            else:
                curr = GcodePreprocessorUtils.evalQuadraticBSpline(t, start, p_cp1, end)
                nxt = GcodePreprocessorUtils.evalQuadraticBSpline(t_next, start, p_cp1, end)
                mid = GcodePreprocessorUtils.evalQuadraticBSpline(t_mid, start, p_cp1, end)

            curr.setZ(start.z() + t * (end.z() - start.z()))
            nxt.setZ(start.z() + t_next * (end.z() - start.z()))
            mid.setZ(start.z() + t_mid * (end.z() - start.z()))

            linear_mid = 0.5 * (curr + nxt)
            dx = mid.x() - linear_mid.x()
            dy = mid.y() - linear_mid.y()
            error = math.sqrt(dx * dx + dy * dy)

            if error < tolerance:
                points.append(nxt)
                t = t_next
                if step < MAX_STEP:
                    step = min(step * 2.0, MAX_STEP)
            else:
                step /= 2.0
                if step < MIN_STEP:
                    points.append(nxt)
                    t = min(t + MIN_STEP, 1.0)
                    step = MIN_STEP

            if len(points) > 1000:
                break

        if points and (points[-1] - end).length() <= 0.001:
            points.pop()
        points.append(end)

        return points

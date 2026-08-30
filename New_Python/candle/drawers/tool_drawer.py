"""3D Tool / Cutter OpenGL drawer with spinning animation."""

import math
from typing import List
from PyQt6.QtGui import QVector3D, QColor
from ..config import VertexDataType
from .shader_drawable import ShaderDrawable, VertexData


class ToolDrawer(ShaderDrawable):
    def __init__(self):
        super().__init__()
        self.m_toolDiameter: float = 3.175
        self.m_toolLength: float = 20.0
        self.m_toolAngle: float = 0.0  # 0 for flat endmill / cylinder, > 0 for V-bit / cone
        self.m_toolPosition: QVector3D = QVector3D(0, 0, 0)
        self.m_spinAngle: float = 0.0
        self.m_endLength: float = 0.0
        self.m_color: QColor = QColor(255, 153, 0)

        self._adjust_tool_end_length()

    def updateData(self) -> bool:
        arcs = 4
        self.m_lines.clear()
        self.m_points.clear()
        self.m_triangles.clear()

        color_vec = QVector3D(self.m_color.redF(), self.m_color.greenF(), self.m_color.blueF())

        # Bottom circle
        self.m_lines.extend(self._create_circle(
            QVector3D(self.m_toolPosition.x(), self.m_toolPosition.y(), self.m_toolPosition.z() + self.m_endLength),
            self.m_toolDiameter / 2.0, 20, color_vec
        ))

        # Top circle
        self.m_lines.extend(self._create_circle(
            QVector3D(self.m_toolPosition.x(), self.m_toolPosition.y(), self.m_toolPosition.z() + self.m_toolLength),
            self.m_toolDiameter / 2.0, 20, color_vec
        ))

        # Zero Z shadow circle
        if self.m_endLength == 0:
            self.m_lines.extend(self._create_circle(
                QVector3D(self.m_toolPosition.x(), self.m_toolPosition.y(), 0),
                self.m_toolDiameter / 2.0, 20, color_vec
            ))

        # Flutes / side lines
        for i in range(arcs):
            ang = self.m_spinAngle / 180.0 * math.pi + (2.0 * math.pi / arcs) * i
            x = self.m_toolPosition.x() + self.m_toolDiameter / 2.0 * math.cos(ang)
            y = self.m_toolPosition.y() + self.m_toolDiameter / 2.0 * math.sin(ang)

            # Side line
            self.m_lines.append(VertexData(
                QVector3D(x, y, self.m_toolPosition.z() + self.m_endLength),
                color_vec, QVector3D(), float(VertexDataType.Line)
            ))
            self.m_lines.append(VertexData(
                QVector3D(x, y, self.m_toolPosition.z() + self.m_toolLength),
                color_vec, QVector3D(), float(VertexDataType.Line)
            ))

            # Tip/bottom line
            self.m_lines.append(VertexData(
                QVector3D(self.m_toolPosition.x(), self.m_toolPosition.y(), self.m_toolPosition.z()),
                color_vec, QVector3D(), float(VertexDataType.Line)
            ))
            self.m_lines.append(VertexData(
                QVector3D(x, y, self.m_toolPosition.z() + self.m_endLength),
                color_vec, QVector3D(), float(VertexDataType.Line)
            ))

            # Top cross
            self.m_lines.append(VertexData(
                QVector3D(self.m_toolPosition.x(), self.m_toolPosition.y(), self.m_toolPosition.z() + self.m_toolLength),
                color_vec, QVector3D(), float(VertexDataType.Line)
            ))
            self.m_lines.append(VertexData(
                QVector3D(x, y, self.m_toolPosition.z() + self.m_toolLength),
                color_vec, QVector3D(), float(VertexDataType.Line)
            ))

        return True

    def _create_circle(self, center: QVector3D, radius: float, arcs: int, color: QVector3D) -> List[VertexData]:
        circle: List[VertexData] = []
        for i in range(arcs + 1):
            angle = 2.0 * math.pi * i / arcs
            x = center.x() + radius * math.cos(angle)
            y = center.y() + radius * math.sin(angle)

            if i > 1:
                circle.append(circle[-1])
            elif i == arcs:
                circle.append(circle[0])

            circle.append(VertexData(QVector3D(x, y, center.z()), color, QVector3D(), float(VertexDataType.Line)))
        return circle

    def toolDiameter(self) -> float: return self.m_toolDiameter
    def setToolDiameter(self, d: float): self.m_toolDiameter = d; self._adjust_tool_end_length(); self.update()

    def toolLength(self) -> float: return self.m_toolLength
    def setToolLength(self, l: float): self.m_toolLength = l; self._adjust_tool_end_length(); self.update()

    def toolAngle(self) -> float: return self.m_toolAngle
    def setToolAngle(self, a: float): self.m_toolAngle = a; self._adjust_tool_end_length(); self.update()

    def toolPosition(self) -> QVector3D: return self.m_toolPosition
    def setToolPosition(self, p: QVector3D): self.m_toolPosition = QVector3D(p); self.update()

    def spinAngle(self) -> float: return self.m_spinAngle
    def setSpinAngle(self, a: float): self.m_spinAngle = a; self.update()

    def spin(self, delta: float):
        ang = (self.m_spinAngle + delta) % 360.0
        self.setSpinAngle(ang)

    def color(self) -> QColor: return self.m_color
    def setColor(self, c: QColor): self.m_color = c; self.update()

    def _adjust_tool_end_length(self):
        if 0 < self.m_toolAngle < 180:
            self.m_endLength = self.m_toolDiameter / 2.0 / math.tan(self.m_toolAngle / 180.0 * math.pi / 2.0)
        else:
            self.m_endLength = 0.0
        if self.m_toolLength < self.m_endLength:
            self.m_toolLength = self.m_endLength

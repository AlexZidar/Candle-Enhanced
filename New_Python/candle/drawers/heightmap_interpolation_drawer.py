"""Bicubic interpolated surface mesh with HSV color elevation gradient OpenGL drawer."""

import math
from typing import List
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QVector3D, QColor
from ..config import VertexDataType
from .shader_drawable import ShaderDrawable, VertexData


class HeightMapInterpolationDrawer(ShaderDrawable):
    def __init__(self):
        super().__init__()
        self.m_borderRect: QRectF = QRectF(0, 0, 100, 100)
        self.m_data: List[List[float]] = []

    def setBorderRect(self, r: QRectF):
        self.m_borderRect = QRectF(r)
        self.update()

    def setData(self, data: List[List[float]]):
        self.m_data = data
        self.update()

    def clear(self):
        self.m_data = []
        self.update()

    def updateData(self) -> bool:
        self.m_lines.clear()
        self.m_points.clear()
        self.m_triangles.clear()

        if not self.m_data or len(self.m_data) < 2 or len(self.m_data[0]) < 2:
            return True

        rows = len(self.m_data)
        cols = len(self.m_data[0])

        step_x = self.m_borderRect.width() / (cols - 1) if cols > 1 else 0.0
        step_y = self.m_borderRect.height() / (rows - 1) if rows > 1 else 0.0

        # Find min and max
        min_z = float('inf')
        max_z = float('-inf')
        for r in self.m_data:
            for v in r:
                if not math.isnan(v):
                    min_z = min(min_z, v)
                    max_z = max(max_z, v)

        if math.isinf(min_z) or math.isinf(max_z):
            return True

        z_range = max_z - min_z if max_z != min_z else 1.0

        def get_color(z: float) -> QVector3D:
            if math.isnan(z):
                return QVector3D(0.5, 0.5, 0.5)
            h = 0.67 * (max_z - z) / z_range
            c = QColor.fromHsvF(max(0.0, min(1.0, h)), 1.0, 1.0)
            return QVector3D(c.redF(), c.greenF(), c.blueF())

        # Horizontal lines
        for i in range(rows):
            for j in range(1, cols):
                z1 = self.m_data[i][j - 1]
                z2 = self.m_data[i][j]
                if math.isnan(z1) or math.isnan(z2):
                    continue
                x1 = self.m_borderRect.x() + step_x * (j - 1)
                x2 = self.m_borderRect.x() + step_x * j
                y = self.m_borderRect.y() + step_y * i

                self.m_lines.append(VertexData(QVector3D(x1, y, z1), get_color(z1), QVector3D(), float(VertexDataType.Line)))
                self.m_lines.append(VertexData(QVector3D(x2, y, z2), get_color(z2), QVector3D(), float(VertexDataType.Line)))

        # Vertical lines
        for j in range(cols):
            for i in range(1, rows):
                z1 = self.m_data[i - 1][j]
                z2 = self.m_data[i][j]
                if math.isnan(z1) or math.isnan(z2):
                    continue
                x = self.m_borderRect.x() + step_x * j
                y1 = self.m_borderRect.y() + step_y * (i - 1)
                y2 = self.m_borderRect.y() + step_y * i

                self.m_lines.append(VertexData(QVector3D(x, y1, z1), get_color(z1), QVector3D(), float(VertexDataType.Line)))
                self.m_lines.append(VertexData(QVector3D(x, y2, z2), get_color(z2), QVector3D(), float(VertexDataType.Line)))

        return True

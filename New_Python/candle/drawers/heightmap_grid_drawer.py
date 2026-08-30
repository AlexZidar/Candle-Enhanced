"""Heightmap probe grid lines and points OpenGL drawer."""

import math
from typing import Optional
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QVector3D
from ..config import VertexDataType
from .shader_drawable import ShaderDrawable, VertexData
from ..heightmap.heightmap_model import HeightMapTableModel


class HeightMapGridDrawer(ShaderDrawable):
    def __init__(self):
        super().__init__()
        self.m_model: Optional[HeightMapTableModel] = None
        self.m_borderRect: QRectF = QRectF(0, 0, 100, 100)
        self.m_zTop: float = 2.0
        self.m_zBottom: float = -2.0
        self.m_pointSize: float = 4.0

    def setModel(self, model: Optional[HeightMapTableModel]):
        self.m_model = model
        self.update()

    def setBorderRect(self, r: QRectF):
        self.m_borderRect = QRectF(r)
        self.update()

    def setZLimits(self, z_top: float, z_bottom: float):
        self.m_zTop = z_top
        self.m_zBottom = z_bottom
        self.update()

    def updateData(self) -> bool:
        self.m_lines.clear()
        self.m_points.clear()
        self.m_triangles.clear()

        if self.m_model is None:
            return False

        grid_x = self.m_model.columnCount()
        grid_y = self.m_model.rowCount()
        if grid_x < 1 or grid_y < 1:
            return False

        step_x = self.m_borderRect.width() / (grid_x - 1) if grid_x > 1 else 0.0
        step_y = self.m_borderRect.height() / (grid_y - 1) if grid_y > 1 else 0.0

        c_unprobed = QVector3D(1.0, 0.6, 0.0)
        c_probed = QVector3D(0.0, 0.0, 1.0)

        # Points & probe columns
        for i in range(grid_y):
            for j in range(grid_x):
                val = self.m_model.data(self.m_model.index(i, j), Qt.ItemDataRole.UserRole)
                x = self.m_borderRect.x() + step_x * j
                y = self.m_borderRect.y() + step_y * i

                if val is None or math.isnan(float(val)):
                    self.m_lines.append(VertexData(QVector3D(x, y, self.m_zTop), c_unprobed, QVector3D(), float(VertexDataType.Line)))
                    self.m_lines.append(VertexData(QVector3D(x, y, self.m_zBottom), c_unprobed, QVector3D(), float(VertexDataType.Line)))
                else:
                    z = float(val)
                    self.m_points.append(VertexData(QVector3D(x, y, z), c_probed, QVector3D(self.m_pointSize, 0, 0), float(VertexDataType.Point)))

        # Horizontal grid lines
        for i in range(grid_y):
            for j in range(1, grid_x):
                v1 = self.m_model.data(self.m_model.index(i, j - 1), Qt.ItemDataRole.UserRole)
                v2 = self.m_model.data(self.m_model.index(i, j), Qt.ItemDataRole.UserRole)
                if v1 is None or v2 is None or math.isnan(float(v1)) or math.isnan(float(v2)):
                    continue
                x1 = self.m_borderRect.x() + step_x * (j - 1)
                x2 = self.m_borderRect.x() + step_x * j
                y = self.m_borderRect.y() + step_y * i
                self.m_lines.append(VertexData(QVector3D(x1, y, float(v1)), c_probed, QVector3D(), float(VertexDataType.Line)))
                self.m_lines.append(VertexData(QVector3D(x2, y, float(v2)), c_probed, QVector3D(), float(VertexDataType.Line)))

        # Vertical grid lines
        for j in range(grid_x):
            for i in range(1, grid_y):
                v1 = self.m_model.data(self.m_model.index(i - 1, j), Qt.ItemDataRole.UserRole)
                v2 = self.m_model.data(self.m_model.index(i, j), Qt.ItemDataRole.UserRole)
                if v1 is None or v2 is None or math.isnan(float(v1)) or math.isnan(float(v2)):
                    continue
                x = self.m_borderRect.x() + step_x * j
                y1 = self.m_borderRect.y() + step_y * (i - 1)
                y2 = self.m_borderRect.y() + step_y * i
                self.m_lines.append(VertexData(QVector3D(x, y1, float(v1)), c_probed, QVector3D(), float(VertexDataType.Line)))
                self.m_lines.append(VertexData(QVector3D(x, y2, float(v2)), c_probed, QVector3D(), float(VertexDataType.Line)))

        return True

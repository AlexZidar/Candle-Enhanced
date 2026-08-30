"""Heightmap boundary box OpenGL drawer."""

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QVector3D, QColor
from ..config import VertexDataType
from .shader_drawable import ShaderDrawable, VertexData


class HeightMapBorderDrawer(ShaderDrawable):
    def __init__(self):
        super().__init__()
        self.m_borderRect: QRectF = QRectF(0, 0, 100, 100)
        self.m_color: QColor = QColor(255, 100, 100)

    def setBorderRect(self, r: QRectF):
        self.m_borderRect = QRectF(r)
        self.update()

    def updateData(self) -> bool:
        self.m_lines.clear()
        self.m_points.clear()
        self.m_triangles.clear()

        c = QVector3D(self.m_color.redF(), self.m_color.greenF(), self.m_color.blueF())
        x0 = self.m_borderRect.left()
        x1 = self.m_borderRect.right()
        y0 = self.m_borderRect.top()
        y1 = self.m_borderRect.bottom()

        self.m_lines = [
            VertexData(QVector3D(x0, y0, 0), c, QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(x1, y0, 0), c, QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(x1, y0, 0), c, QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(x1, y1, 0), c, QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(x1, y1, 0), c, QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(x0, y1, 0), c, QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(x0, y1, 0), c, QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(x0, y0, 0), c, QVector3D(), float(VertexDataType.Line)),
        ]
        return True

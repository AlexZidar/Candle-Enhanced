"""Machine boundary box and workspace grid OpenGL drawer."""

from typing import List
from PyQt6.QtGui import QVector3D, QColor
from ..config import VertexDataType
from .shader_drawable import ShaderDrawable, VertexData


class MachineBoundsDrawer(ShaderDrawable):
    def __init__(self):
        super().__init__()
        self.m_sizeX: float = 300.0
        self.m_sizeY: float = 180.0
        self.m_sizeZ: float = 45.0
        self.m_gridStep: float = 10.0
        self.m_colorBox: QColor = QColor(80, 80, 80)
        self.m_colorGridPrimary: QColor = QColor(64, 64, 64)
        self.m_colorGridSecondary: QColor = QColor(42, 42, 42)

    def updateData(self) -> bool:
        self.m_lines.clear()
        self.m_points.clear()
        self.m_triangles.clear()

        c_box = QVector3D(self.m_colorBox.redF(), self.m_colorBox.greenF(), self.m_colorBox.blueF())
        c_pri = QVector3D(self.m_colorGridPrimary.redF(), self.m_colorGridPrimary.greenF(), self.m_colorGridPrimary.blueF())
        c_sec = QVector3D(self.m_colorGridSecondary.redF(), self.m_colorGridSecondary.greenF(), self.m_colorGridSecondary.blueF())

        # Grid on XY
        if self.m_gridStep > 0:
            nx = int(self.m_sizeX / self.m_gridStep)
            ny = int(self.m_sizeY / self.m_gridStep)

            for i in range(nx + 1):
                x = i * self.m_gridStep
                c = c_pri if (i % 5 == 0) else c_sec
                self.m_lines.append(VertexData(QVector3D(x, 0, 0), c, QVector3D(), float(VertexDataType.Line)))
                self.m_lines.append(VertexData(QVector3D(x, self.m_sizeY, 0), c, QVector3D(), float(VertexDataType.Line)))

            for j in range(ny + 1):
                y = j * self.m_gridStep
                c = c_pri if (j % 5 == 0) else c_sec
                self.m_lines.append(VertexData(QVector3D(0, y, 0), c, QVector3D(), float(VertexDataType.Line)))
                self.m_lines.append(VertexData(QVector3D(self.m_sizeX, y, 0), c, QVector3D(), float(VertexDataType.Line)))

        # Machine Volume Wireframe Box
        sx, sy, sz = self.m_sizeX, self.m_sizeY, -self.m_sizeZ  # Machine coordinate Z is down from 0 to -Z

        # Top rectangle (Z=0)
        self.m_lines.append(VertexData(QVector3D(0, 0, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, 0, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, 0, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, sy, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, sy, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(0, sy, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(0, sy, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(0, 0, 0), c_box, QVector3D(), float(VertexDataType.Line)))

        # Bottom rectangle (Z=-sz)
        self.m_lines.append(VertexData(QVector3D(0, 0, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, 0, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, 0, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, sy, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, sy, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(0, sy, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(0, sy, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(0, 0, sz), c_box, QVector3D(), float(VertexDataType.Line)))

        # 4 vertical pillars
        self.m_lines.append(VertexData(QVector3D(0, 0, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(0, 0, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, 0, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, 0, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, sy, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(sx, sy, sz), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(0, sy, 0), c_box, QVector3D(), float(VertexDataType.Line)))
        self.m_lines.append(VertexData(QVector3D(0, sy, sz), c_box, QVector3D(), float(VertexDataType.Line)))

        return True

    def setDimensions(self, x: float, y: float, z: float):
        self.m_sizeX, self.m_sizeY, self.m_sizeZ = x, y, z
        self.update()

    def setColors(self, primary: QColor, secondary: QColor):
        self.m_colorGridPrimary = primary
        self.m_colorGridSecondary = secondary
        self.update()

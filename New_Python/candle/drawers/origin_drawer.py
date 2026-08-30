"""3D Origin Tripod with X, Y, Z axis arrows and labels."""

from PyQt6.QtGui import QVector3D
from ..config import VertexDataType
from .shader_drawable import ShaderDrawable, VertexData


class OriginDrawer(ShaderDrawable):
    def __init__(self):
        super().__init__()
        self.setWorldScale(10.0)

    def updateData(self) -> bool:
        self.m_lines = [
            # X-axis (Red)
            VertexData(QVector3D(0, 0, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(1.0, 0, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.8, 0.05, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(1.0, 0, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.8, -0.05, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(1.0, 0, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),

            # Y-axis (Green)
            VertexData(QVector3D(0, 0, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0, 1.0, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(-0.05, 0.8, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0, 1.0, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.05, 0.8, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0, 1.0, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),

            # Z-axis (Blue)
            VertexData(QVector3D(0, 0, 0), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0, 0, 1.0), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(-0.05, 0, 0.8), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0, 0, 1.0), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.05, 0, 0.8), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0, 0, 1.0), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),

            # 2x2 rect base
            VertexData(QVector3D(0.1, 0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(-0.1, 0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(-0.1, 0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(-0.1, -0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(-0.1, -0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.1, -0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.1, -0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.1, 0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),

            # X label
            VertexData(QVector3D(0.85, 0.3, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(1.0, 0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.85, 0.1, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(1.0, 0.3, 0), QVector3D(1.0, 0, 0), QVector3D(), float(VertexDataType.Line)),

            # Y label
            VertexData(QVector3D(0.1, 1.0, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.175, 0.9, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.175, 0.9, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.25, 1.0, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.175, 0.9, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.175, 0.8, 0), QVector3D(0, 1.0, 0), QVector3D(), float(VertexDataType.Line)),

            # Z label
            VertexData(QVector3D(0.1, 0, 0.8), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.25, 0, 0.8), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.1, 0, 0.8), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.25, 0, 1.0), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.1, 0, 1.0), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line)),
            VertexData(QVector3D(0.25, 0, 1.0), QVector3D(0, 0, 1.0), QVector3D(), float(VertexDataType.Line))
        ]
        return True

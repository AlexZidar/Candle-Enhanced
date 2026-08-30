"""Base class for all 3D OpenGL renderable objects in Candle."""

import numpy as np
from typing import List, Optional
from OpenGL.GL import *
from PyQt6.QtGui import QVector3D, QMatrix4x4, QPainter
from ..config import VertexDataType


class VertexData:
    def __init__(self, position: QVector3D = QVector3D(), color: QVector3D = QVector3D(1, 1, 1),
                 data: QVector3D = QVector3D(), vertex_type: float = float(VertexDataType.Line)):
        self.position: QVector3D = QVector3D(position)
        self.color: QVector3D = QVector3D(color)
        self.data: QVector3D = QVector3D(data)
        self.type: float = vertex_type


class ShaderDrawable:
    def __init__(self):
        self.m_visible: bool = True
        self.m_lineWidth: float = 1.0
        self.m_pointSize: float = 1.0
        self.m_worldScale: float = 1.0
        self.m_windowScaling: bool = False
        self.m_windowScale: float = 1.0

        self.m_lines: List[VertexData] = []
        self.m_points: List[VertexData] = []
        self.m_triangles: List[VertexData] = []

        self.m_modelMatrix: QMatrix4x4 = QMatrix4x4()
        self.m_translationMatrix: QMatrix4x4 = QMatrix4x4()
        self.m_rotationMatrix: QMatrix4x4 = QMatrix4x4()
        self.m_scaleMatrix: QMatrix4x4 = QMatrix4x4()

        self.m_vao: int = 0
        self.m_vbo: int = 0
        self.m_needsUpdateGeometry: bool = True
        self.m_triCount: int = 0
        self.m_lineCount: int = 0
        self.m_pointCount: int = 0

    def initGL(self) -> None:
        if self.m_vao == 0:
            self.m_vao = glGenVertexArrays(1)
        if self.m_vbo == 0:
            self.m_vbo = glGenBuffers(1)

    def dispose(self) -> None:
        if self.m_vbo:
            glDeleteBuffers(1, [self.m_vbo])
            self.m_vbo = 0
        if self.m_vao:
            glDeleteVertexArrays(1, [self.m_vao])
            self.m_vao = 0

    def update(self) -> None:
        self.m_needsUpdateGeometry = True

    def needsUpdateGeometry(self) -> bool:
        return self.m_needsUpdateGeometry

    def updateData(self) -> bool:
        return False

    def updateGeometry(self, shader_program) -> None:
        self.initGL()

        if not self.updateData():
            self.m_needsUpdateGeometry = False
            return

        self.m_triCount = len(self.m_triangles)
        self.m_lineCount = len(self.m_lines)
        self.m_pointCount = len(self.m_points)
        total_verts = self.m_triCount + self.m_lineCount + self.m_pointCount

        if total_verts == 0:
            self.m_needsUpdateGeometry = False
            return

        buffer_data = np.empty((total_verts, 10), dtype=np.float32)

        idx = 0
        for group in (self.m_triangles, self.m_lines, self.m_points):
            for v in group:
                buffer_data[idx, 0] = v.position.x()
                buffer_data[idx, 1] = v.position.y()
                buffer_data[idx, 2] = v.position.z()
                buffer_data[idx, 3] = v.color.x()
                buffer_data[idx, 4] = v.color.y()
                buffer_data[idx, 5] = v.color.z()
                buffer_data[idx, 6] = v.data.x()
                buffer_data[idx, 7] = v.data.y()
                buffer_data[idx, 8] = v.data.z()
                buffer_data[idx, 9] = v.type
                idx += 1

        glBindVertexArray(self.m_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.m_vbo)
        glBufferData(GL_ARRAY_BUFFER, buffer_data.nbytes, buffer_data, GL_DYNAMIC_DRAW)

        stride = 10 * 4  # 10 floats, 4 bytes each = 40 bytes

        loc_pos = shader_program.attributeLocation("a_position")
        if loc_pos != -1:
            glEnableVertexAttribArray(loc_pos)
            glVertexAttribPointer(loc_pos, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))

        loc_color = shader_program.attributeLocation("a_color")
        if loc_color != -1:
            glEnableVertexAttribArray(loc_color)
            glVertexAttribPointer(loc_color, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))

        loc_data = shader_program.attributeLocation("a_data")
        if loc_data != -1:
            glEnableVertexAttribArray(loc_data)
            glVertexAttribPointer(loc_data, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))

        loc_type = shader_program.attributeLocation("a_type")
        if loc_type != -1:
            glEnableVertexAttribArray(loc_type)
            glVertexAttribPointer(loc_type, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(36))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        self.m_needsUpdateGeometry = False

    def draw(self, shader_program) -> None:
        if not self.m_visible:
            return

        total_verts = self.m_triCount + self.m_lineCount + self.m_pointCount
        if total_verts == 0 or self.m_vao == 0:
            return

        glBindVertexArray(self.m_vao)

        if self.m_triCount > 0:
            glDrawArrays(GL_TRIANGLES, 0, self.m_triCount)

        if self.m_lineCount > 0:
            glLineWidth(max(1.0, float(self.m_lineWidth)))
            glDrawArrays(GL_LINES, self.m_triCount, self.m_lineCount)

        if self.m_pointCount > 0:
            glPointSize(max(1.0, float(self.m_pointSize)))
            glDrawArrays(GL_POINTS, self.m_triCount + self.m_lineCount, self.m_pointCount)

        glBindVertexArray(0)

    def drawPainter(self, painter: QPainter, projection: QMatrix4x4, ratio: float) -> None:
        """2D overlay painter hook."""
        pass

    def getViewRanges(self) -> QVector3D:
        return self.getViewUpperBounds() - self.getViewLowerBounds()

    def getViewLowerBounds(self) -> QVector3D:
        return QVector3D()

    def getViewUpperBounds(self) -> QVector3D:
        return QVector3D()

    def getModelRanges(self) -> QVector3D:
        return self.getModelUpperBounds() - self.getModelLowerBounds()

    def getModelLowerBounds(self) -> QVector3D:
        return QVector3D()

    def getModelUpperBounds(self) -> QVector3D:
        return QVector3D()

    def getVertexCount(self) -> int:
        return self.m_triCount + self.m_lineCount + self.m_pointCount

    def lineWidth(self) -> float:
        return self.m_lineWidth

    def setLineWidth(self, w: float) -> None:
        self.m_lineWidth = w

    def pointSize(self) -> float:
        return self.m_pointSize

    def setPointSize(self, s: float) -> None:
        self.m_pointSize = s

    def visible(self) -> bool:
        return self.m_visible

    def setVisible(self, v: bool) -> None:
        self.m_visible = v

    def modelMatrix(self) -> QMatrix4x4:
        m = QMatrix4x4()
        m.setToIdentity()
        m *= self.m_translationMatrix
        m *= self.m_rotationMatrix
        m *= self.m_scaleMatrix
        m.scale(self.m_worldScale)
        return m

    def setRotation(self, angle_or_matrix, axis: Optional[QVector3D] = None) -> None:
        if isinstance(angle_or_matrix, QMatrix4x4):
            self.m_rotationMatrix = QMatrix4x4(angle_or_matrix)
        elif axis is not None:
            self.m_rotationMatrix.setToIdentity()
            self.m_rotationMatrix.rotate(float(angle_or_matrix), axis)

    def rotation(self) -> QMatrix4x4:
        return self.m_rotationMatrix

    def setTranslation(self, translation: QVector3D) -> None:
        self.m_translationMatrix.setToIdentity()
        self.m_translationMatrix.translate(translation)

    def translation(self) -> QMatrix4x4:
        return self.m_translationMatrix

    def setWorldScale(self, scale: float) -> None:
        self.m_worldScale = scale

    def worldScale(self) -> float:
        return self.m_worldScale

    def setWindowScaling(self, val: bool) -> None:
        self.m_windowScaling = val

    def windowScaling(self) -> bool:
        return self.m_windowScaling

    def setWindowScale(self, val: float) -> None:
        self.m_windowScale = val

    def windowScale(self) -> float:
        return self.m_windowScale

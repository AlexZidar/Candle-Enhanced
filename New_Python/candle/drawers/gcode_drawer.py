"""G-code toolpath OpenGL visualizer drawer."""

import math
from typing import List, Optional
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QVector3D, QColor, QPainter, QPolygon, QPen, QBrush
from PyQt6.QtCore import QPoint
from ..config import VertexDataType, DrawMode, GrayscaleCode
from .shader_drawable import ShaderDrawable, VertexData
from ..parser.gcode_view_parser import GcodeViewParse
from ..parser.line_segment import LineSegment


def _color_to_vec(color: QColor) -> QVector3D:
    return QVector3D(color.redF(), color.greenF(), color.blueF())


class GcodeDrawer(QObject, ShaderDrawable):
    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        ShaderDrawable.__init__(self)

        self.m_viewParser: Optional[GcodeViewParse] = None
        self.m_geometryUpdated: bool = False
        self.m_pointSize: float = 6.0
        self.m_ignoreZ: bool = False
        self.m_grayscaleSegments: bool = False
        self.m_grayscaleCode: GrayscaleCode = GrayscaleCode.S
        self.m_grayscaleMin: int = 0
        self.m_grayscaleMax: int = 255
        self.m_drawMode: DrawMode = DrawMode.Vectors
        self.m_simplify: bool = False
        self.m_simplifyPrecision: float = 0.05

        self.m_start: QVector3D = QVector3D(float('nan'), float('nan'), float('nan'))
        self.m_end: QVector3D = QVector3D(float('nan'), float('nan'), float('nan'))

        self.m_colorNormal: QColor = QColor(77, 144, 254)
        self.m_colorDrawn: QColor = QColor(136, 136, 136)
        self.m_colorHighlight: QColor = QColor(255, 255, 0)
        self.m_colorZMovement: QColor = QColor(255, 51, 51)
        self.m_colorStart: QColor = QColor(0, 255, 0)
        self.m_colorEnd: QColor = QColor(255, 0, 0)

        self.m_indexes: List[int] = []

        self.m_timerVertexUpdate = QTimer(self)
        self.m_timerVertexUpdate.timeout.connect(self._on_timer_vertex_update)
        self.m_timerVertexUpdate.start(25)

    def setViewParser(self, parser: GcodeViewParse) -> None:
        self.m_viewParser = parser

    def viewParser(self) -> Optional[GcodeViewParse]:
        return self.m_viewParser

    def update(self, indexes: Optional[List[int]] = None) -> None:
        if indexes is None:
            self.m_indexes.clear()
            self.m_geometryUpdated = False
            ShaderDrawable.update(self)
        else:
            self.m_indexes.extend(indexes)

    def _on_timer_vertex_update(self) -> None:
        if self.m_indexes:
            ShaderDrawable.update(self)

    def getViewLowerBounds(self) -> QVector3D:
        return self.m_viewParser.getViewLowerBounds() if self.m_viewParser else QVector3D()

    def getViewUpperBounds(self) -> QVector3D:
        return self.m_viewParser.getViewUpperBounds() if self.m_viewParser else QVector3D()

    def getModelLowerBounds(self) -> QVector3D:
        return self.m_viewParser.getModelLowerBounds() if self.m_viewParser else QVector3D()

    def getModelUpperBounds(self) -> QVector3D:
        return self.m_viewParser.getModelUpperBounds() if self.m_viewParser else QVector3D()

    def updateData(self) -> bool:
        if not self.m_viewParser:
            return False
        return self.prepareVectors()

    def drawPainter(self, painter: QPainter, projection, ratio: float) -> None:
        polygon = QPolygon([QPoint(0, 0), QPoint(-4, 32), QPoint(4, 32), QPoint(0, 0)])
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not math.isnan(self.m_start.x()):
            painter.save()
            pt = projection.map(self.m_start).toPoint()
            painter.translate(pt)
            painter.scale(1, -1)
            painter.setPen(QPen(self.m_colorStart))
            painter.setBrush(QBrush(self.m_colorStart))
            painter.drawPolygon(polygon)
            painter.restore()

        if not math.isnan(self.m_end.x()):
            painter.save()
            pt = projection.map(self.m_end).toPoint()
            painter.translate(pt)
            painter.scale(1, -1)
            painter.setPen(QPen(self.m_colorEnd))
            painter.setBrush(QBrush(self.m_colorEnd))
            painter.drawPolygon(polygon)
            painter.restore()

    def prepareVectors(self) -> bool:
        self.m_lines.clear()
        self.m_points.clear()
        self.m_triangles.clear()
        self.m_start = QVector3D(float('nan'), float('nan'), float('nan'))
        self.m_end = QVector3D(float('nan'), float('nan'), float('nan'))

        if not self.m_viewParser:
            return False

        line_segments = self.m_viewParser.getLineSegments()
        is_first_point_added = False
        line_count = len(line_segments)

        for i in range(line_count):
            line_seg = line_segments[i]
            if not is_first_point_added:
                if math.isnan(line_seg.getEnd().x()) or math.isnan(line_seg.getEnd().y()):
                    continue
                self.m_start = QVector3D(line_seg.getEnd())
                if self.m_ignoreZ or math.isnan(self.m_start.z()):
                    self.m_start.setZ(0)
                is_first_point_added = True
                continue

            v_type = float(VertexDataType.Dash) if line_seg.isFastTraverse else float(VertexDataType.Line)
            v_data = line_seg.getStart() if line_seg.isFastTraverse else QVector3D()
            color = self.getSegmentColorVector(line_seg)

            line_seg.setVertexIndex(len(self.m_lines))

            # Line start
            p_start = QVector3D(line_seg.getStart())
            if self.m_ignoreZ or math.isnan(p_start.z()):
                p_start.setZ(0)
            self.m_lines.append(VertexData(p_start, color, v_data, v_type))

            # Line end
            p_end = QVector3D(line_seg.getEnd())
            if self.m_ignoreZ or math.isnan(p_end.z()):
                p_end.setZ(0)
            self.m_lines.append(VertexData(p_end, color, v_data, v_type))

            if i == line_count - 1:
                self.m_end = QVector3D(p_end)

        self.m_geometryUpdated = True
        self.m_indexes.clear()
        return True

    def getSegmentColorVector(self, segment: LineSegment) -> QVector3D:
        if segment.isHighlight:
            return _color_to_vec(self.m_colorHighlight)
        if segment.isDrawn:
            return _color_to_vec(self.m_colorDrawn)
        if segment.isZMovement:
            return _color_to_vec(self.m_colorZMovement)

        if self.m_grayscaleSegments:
            if self.m_grayscaleCode == GrayscaleCode.S:
                s = segment.getSpindleSpeed()
                c = (s - self.m_grayscaleMin) / max(1.0, float(self.m_grayscaleMax - self.m_grayscaleMin))
            else:
                z = segment.getEnd().z()
                c = (z - self.m_grayscaleMin) / max(1.0, float(self.m_grayscaleMax - self.m_grayscaleMin))
            c = max(0.0, min(1.0, c))
            return QVector3D(c, c, c)

        return _color_to_vec(self.m_colorNormal)

    # Getters & setters
    def colorNormal(self) -> QColor: return self.m_colorNormal
    def setColorNormal(self, c: QColor): self.m_colorNormal = c; self.update()
    def colorHighlight(self) -> QColor: return self.m_colorHighlight
    def setColorHighlight(self, c: QColor): self.m_colorHighlight = c; self.update()
    def colorZMovement(self) -> QColor: return self.m_colorZMovement
    def setColorZMovement(self, c: QColor): self.m_colorZMovement = c; self.update()
    def colorDrawn(self) -> QColor: return self.m_colorDrawn
    def setColorDrawn(self, c: QColor): self.m_colorDrawn = c; self.update()
    def colorStart(self) -> QColor: return self.m_colorStart
    def setColorStart(self, c: QColor): self.m_colorStart = c; self.update()
    def colorEnd(self) -> QColor: return self.m_colorEnd
    def setColorEnd(self, c: QColor): self.m_colorEnd = c; self.update()

    def getIgnoreZ(self) -> bool: return self.m_ignoreZ
    def setIgnoreZ(self, val: bool): self.m_ignoreZ = val; self.update()
    def getGrayscaleSegments(self) -> bool: return self.m_grayscaleSegments
    def setGrayscaleSegments(self, val: bool): self.m_grayscaleSegments = val; self.update()
    def grayscaleCode(self) -> GrayscaleCode: return self.m_grayscaleCode
    def setGrayscaleCode(self, code: GrayscaleCode): self.m_grayscaleCode = code; self.update()
    def grayscaleMin(self) -> int: return self.m_grayscaleMin
    def setGrayscaleMin(self, val: int): self.m_grayscaleMin = val; self.update()
    def grayscaleMax(self) -> int: return self.m_grayscaleMax
    def setGrayscaleMax(self, val: int): self.m_grayscaleMax = val; self.update()
    def drawMode(self) -> DrawMode: return self.m_drawMode
    def setDrawMode(self, mode: DrawMode): self.m_drawMode = mode; self.update()
    def simplify(self) -> bool: return self.m_simplify
    def setSimplify(self, val: bool): self.m_simplify = val; self.update()
    def simplifyPrecision(self) -> float: return self.m_simplifyPrecision
    def setSimplifyPrecision(self, val: float): self.m_simplifyPrecision = val; self.update()

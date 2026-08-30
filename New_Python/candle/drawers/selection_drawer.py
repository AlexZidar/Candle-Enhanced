"""Selection indicator arrow drawer for highlighting selected toolpath line."""

from PyQt6.QtGui import QVector3D, QColor, QPainter, QPolygon, QPen, QBrush
from PyQt6.QtCore import QPoint
from .shader_drawable import ShaderDrawable


class SelectionDrawer(ShaderDrawable):
    def __init__(self):
        super().__init__()
        self.m_position: QVector3D = QVector3D()
        self.m_color: QColor = QColor(255, 255, 0)

    def drawPainter(self, painter: QPainter, projection, ratio: float) -> None:
        polygon = QPolygon([QPoint(0, 0), QPoint(-4, 32), QPoint(4, 32), QPoint(0, 0)])
        painter.save()
        pt = projection.map(self.m_position).toPoint()
        painter.translate(pt)
        painter.scale(1, -1)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.m_color))
        painter.setBrush(QBrush(self.m_color))
        painter.drawPolygon(polygon)
        painter.restore()

    def color(self) -> QColor: return self.m_color
    def setColor(self, c: QColor): self.m_color = c; self.update()

    def position(self) -> QVector3D: return self.m_position
    def setPosition(self, p: QVector3D): self.m_position = QVector3D(p); self.update()

"""2D HUD Overlay for 3D Visualizer."""

from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt, QPoint, QTime
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QFontMetrics, QPen, QMatrix4x4

if TYPE_CHECKING:
    from .gl_widget import GLWidget


class Overlay(QWidget):
    def __init__(self, parent: 'GLWidget'):
        super().__init__(parent)
        self.m_parent: 'GLWidget' = parent
        self.setStyleSheet("color: white; background: transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        fm = QFontMetrics(painter.font())

        xbounds = f"X: {self.m_parent.m_modelLowerBounds.x():.3f} ... {self.m_parent.m_modelUpperBounds.x():.3f} ({self.m_parent.m_cursorPos.x():.3f})"
        ybounds = f"Y: {self.m_parent.m_modelLowerBounds.y():.3f} ... {self.m_parent.m_modelUpperBounds.y():.3f} ({self.m_parent.m_cursorPos.y():.3f})"
        zbounds = f"Z: {self.m_parent.m_modelLowerBounds.z():.3f} ... {self.m_parent.m_modelUpperBounds.z():.3f} ({self.m_parent.m_cursorPos.z():.3f})"
        ranges = f"{self.m_parent.m_modelRanges.x():.3f} / {self.m_parent.m_modelRanges.y():.3f} / {self.m_parent.m_modelRanges.z():.3f}"
        vertices = f"Vertices: {self.m_parent.m_vertices}"
        fps = f"FPS: {self.m_parent.m_fps}"

        spend_str = self.m_parent.m_spendTime.toString("hh:mm:ss")
        est_str = self.m_parent.m_estimatedTime.toString("hh:mm:ss")
        estimate = f"{spend_str} / {est_str}"
        buffer_str = self.m_parent.m_bufferState

        x = 10
        y = self.height() - fm.height() * 3 - 10

        pen = QPen(self.m_parent.m_colorText)
        painter.setPen(pen)

        # Left bottom: Bounds & Ranges
        painter.drawText(QPoint(x, y), xbounds)
        painter.drawText(QPoint(x, y + fm.height()), ybounds)
        painter.drawText(QPoint(x, y + fm.height() * 2), zbounds)
        painter.drawText(QPoint(x, y + fm.height() * 3), ranges)

        # Left top: GRBL Status / Speed / Pins
        painter.drawText(QPoint(x, fm.height() + 10), self.m_parent.m_parserStatus)
        painter.drawText(QPoint(x, fm.height() * 2 + 10), self.m_parent.m_speedState)
        painter.drawText(QPoint(x, fm.height() * 3 + 10), self.m_parent.m_pinState)

        # Right bottom: Stats
        painter.drawText(QPoint(self.width() - fm.horizontalAdvance(vertices) - 10, y + fm.height() * 2), vertices)
        painter.drawText(QPoint(self.width() - fm.horizontalAdvance(fps) - 10, y + fm.height() * 3), fps)
        painter.drawText(QPoint(self.width() - fm.horizontalAdvance(estimate) - 10, y), estimate)
        painter.drawText(QPoint(self.width() - fm.horizontalAdvance(buffer_str) - 10, y + fm.height()), buffer_str)

        if self.m_parent.m_updating:
            updating_text = "Updating..."
            painter.drawText(QPoint(int((self.width() - fm.horizontalAdvance(updating_text)) / 2), y + fm.height() * 3), updating_text)

        # Draw 2D elements from Drawers (like start/end/selection arrows)
        w = QMatrix4x4()
        w.scale(self.width() / 2.0, -self.height() / 2.0)
        w.translate(1.0, -1.0)
        w = w * (self.m_parent.m_projectionMatrix * self.m_parent.m_viewMatrix)

        for drawable in self.m_parent.m_shaderDrawables:
            if drawable.visible():
                painter.save()
                drawable.drawPainter(painter, w * drawable.modelMatrix(), self.height() / (self.m_parent.m_windowSizeWorld or 1.0))
                painter.restore()

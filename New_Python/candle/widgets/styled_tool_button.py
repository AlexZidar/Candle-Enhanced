"""Custom styled tool button with gradient borders, antialiasing, and hover states."""

from typing import Optional
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtWidgets import QToolButton
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPalette, QLinearGradient, QIcon
)


class StyledToolButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_hovered: bool = False
        self.m_backColor: Optional[QColor] = None
        self.m_foreColor: Optional[QColor] = None
        self.m_highlightColor: QColor = QColor(127, 211, 255).darker(120)

    def isHover(self) -> bool:
        return self.m_hovered

    def enterEvent(self, event) -> None:
        self.m_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.m_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        border_width = 4
        border_radius = 5

        back_color = self.backColor()
        fore_color = self.foreColor()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Highlight outer border
        highlight_pen = QPen()
        if (not self.isEnabled() and not self.isChecked()) or (not self.isDown() and not self.isChecked() and not self.isHover()):
            highlight_pen.setColor(self.palette().color(QPalette.ColorRole.Base))
        elif self.isDown() or self.isChecked():
            highlight_pen.setColor(self.m_highlightColor)
        elif self.isHover():
            highlight_pen.setColor(self.m_highlightColor.lighter(120))

        highlight_pen.setWidth(2)
        painter.setPen(highlight_pen)
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, border_radius - 1, border_radius - 1)

        # Outline border
        button_inverted = self.palette().color(QPalette.ColorRole.Button).value() <= 127
        pen = QPen(
            self.palette().color(QPalette.ColorRole.Shadow) if self.isEnabled()
            else self.palette().color(QPalette.ColorRole.Shadow if button_inverted else QPalette.ColorRole.Mid)
        )
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)

        # Background gradient border
        back_inverted = back_color.value() <= 127
        back_grad = QLinearGradient(self.width() / 2.0, self.height() / 2.0, self.width() / 2.0, float(self.height()))
        base_c = back_color if self.isEnabled() else self.palette().color(QPalette.ColorRole.Button)
        end_c = base_c.lighter(200) if back_inverted else base_c.darker(130)
        back_grad.setColorAt(0.0, base_c)
        back_grad.setColorAt(1.0, end_c)

        painter.setBrush(QBrush(back_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(border_width - 1, border_width - 1, self.width() - border_width * 2 + 2, self.height() - border_width * 2 + 2, 2, 2)

        # Inner Background
        painter.setBrush(base_c)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(border_width, border_width, self.width() - border_width * 2, self.height() - border_width * 2)

        # Icon / text rect
        inner_rect = QRect(border_width, border_width, self.width() - border_width * 2, self.height() - border_width * 2)
        if self.isDown() or self.isChecked():
            inner_rect.adjust(2, 2, 2, 2)

        # Icon
        if not self.icon().isNull():
            icon_size = self.icon().actualSize(self.iconSize())
            target_rect = QRect(
                inner_rect.x() + int((inner_rect.width() - icon_size.width()) / 2),
                inner_rect.y() + int((inner_rect.height() - icon_size.height()) / 2),
                icon_size.width(), icon_size.height()
            )
            mode = QIcon.Mode.Normal if self.isEnabled() else QIcon.Mode.Disabled
            painter.drawPixmap(target_rect, self.icon().pixmap(icon_size, mode))
        else:
            painter.setPen(fore_color if self.isEnabled() else self.palette().color(QPalette.ColorRole.Mid))
            painter.drawText(inner_rect, Qt.AlignmentFlag.AlignCenter, self.text())

    def highlightColor(self) -> QColor:
        return self.m_highlightColor

    def setHighlightColor(self, c: QColor):
        self.m_highlightColor = c
        self.update()

    def foreColor(self) -> QColor:
        return self.m_foreColor if self.m_foreColor and self.m_foreColor.isValid() else self.palette().color(QPalette.ColorRole.ButtonText)

    def setForeColor(self, c: Optional[QColor]):
        self.m_foreColor = c
        self.update()

    def backColor(self) -> QColor:
        return self.m_backColor if self.m_backColor and self.m_backColor.isValid() else self.palette().color(QPalette.ColorRole.Button)

    def setBackColor(self, c: Optional[QColor]):
        self.m_backColor = c
        self.update()

"""Color Picker PushButton widget for Preferences/Settings dialog."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QPushButton, QColorDialog
from PyQt6.QtGui import QColor


class ColorPickerButton(QPushButton):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, initial_color: QColor = QColor(255, 255, 255), parent=None):
        super().__init__(parent)
        self.m_color: QColor = initial_color
        self.clicked.connect(self._on_click)
        self._update_style()

    def color(self) -> QColor:
        return self.m_color

    def setColor(self, color: QColor):
        self.m_color = color
        self._update_style()
        self.colorChanged.emit(self.m_color)

    def _update_style(self):
        self.setStyleSheet(f"background-color: {self.m_color.name()}; border: 1px solid #555; min-width: 40px; min-height: 20px;")

    def _on_click(self):
        c = QColorDialog.getColor(self.m_color, self, "Select Color")
        if c.isValid():
            self.setColor(c)

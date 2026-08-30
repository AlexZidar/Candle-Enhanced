"""Event filter to ignore mouse wheel events on inputs when scrolling parent containers."""

from PyQt6.QtCore import QObject, QEvent
from PyQt6.QtWidgets import QSlider, QAbstractSpinBox, QComboBox


class NoWheelEventFilter(QObject):
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel:
            if isinstance(obj, (QSlider, QAbstractSpinBox, QComboBox)):
                event.ignore()
                return True
        return super().eventFilter(obj, event)

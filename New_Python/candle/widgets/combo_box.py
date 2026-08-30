"""Custom editable ComboBox with command auto-completion and key event handling."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox


class ComboBoxKey(QComboBox):
    keyPressed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)

    def keyPressEvent(self, event) -> None:
        self.keyPressed.emit(event.key())
        super().keyPressEvent(event)

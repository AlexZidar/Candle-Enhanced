"""Live Logging Output Dock Widget."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
)
from PyQt6.QtGui import QFont


class LogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.txtLog = QTextEdit(self)
        self.txtLog.setFont(QFont("Consolas", 9))
        self.txtLog.setReadOnly(True)
        layout.addWidget(self.txtLog)

        btn_layout = QHBoxLayout()
        self.btnClear = QPushButton("Clear Log", self)
        self.btnClear.clicked.connect(self.txtLog.clear)
        btn_layout.addWidget(self.btnClear)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def appendLog(self, message: str, level: str = "INFO"):
        color = "white"
        if level == "ERROR":
            color = "#ff5555"
        elif level == "WARN":
            color = "#ffff55"
        elif level == "DEBUG":
            color = "#888888"
        self.txtLog.append(f"<span style='color:{color};'>[{level}] {message}</span>")

"""Python Script Editor and Macro Runner Dock Widget."""

import io
import sys
import traceback
from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QSplitter
)
from PyQt6.QtGui import QFont

if TYPE_CHECKING:
    from .main_window import MainWindow


class ScriptWidget(QWidget):
    def __init__(self, main_window: 'MainWindow', parent=None):
        super().__init__(parent)
        self.main_window = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Vertical, self)

        # Editor
        self.txtEditor = QTextEdit(self)
        self.txtEditor.setFont(QFont("Consolas", 10))
        self.txtEditor.setPlaceholderText("# Python Script / Macro for Candle\n# device.sendCommand('G0 X10 Y10')\n# print(device.getCoordinates())")
        self.txtEditor.setPlainText("# Example Macro:\n# device.sendCommand('$H')\n")
        splitter.addWidget(self.txtEditor)

        # Output
        self.txtOutput = QTextEdit(self)
        self.txtOutput.setFont(QFont("Consolas", 9))
        self.txtOutput.setReadOnly(True)
        self.txtOutput.setPlaceholderText("Script Output Console")
        splitter.addWidget(self.txtOutput)

        layout.addWidget(splitter)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btnRun = QPushButton("Run Script", self)
        self.btnRun.clicked.connect(self.runScript)
        self.btnClear = QPushButton("Clear Output", self)
        self.btnClear.clicked.connect(self.txtOutput.clear)

        btn_layout.addWidget(self.btnRun)
        btn_layout.addWidget(self.btnClear)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def runScript(self):
        code = self.txtEditor.toPlainText()
        if not code.strip():
            return

        old_stdout = sys.stdout
        redirected = io.StringIO()
        sys.stdout = redirected

        ctx = {
            "app": self.main_window,
            "device": self.main_window,
            "send": self.main_window.sendConsoleCommand,
        }

        try:
            exec(code, ctx)
            output = redirected.getvalue()
            self.txtOutput.append(output if output else "Script executed successfully.")
        except Exception:
            err = traceback.format_exc()
            self.txtOutput.append(f"<span style='color:red;'>{err}</span>")
        finally:
            sys.stdout = old_stdout

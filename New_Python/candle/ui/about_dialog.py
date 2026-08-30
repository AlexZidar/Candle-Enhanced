"""About Candle Dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QDialogButtonBox
)
from PyQt6.QtGui import QFont, QPixmap
from ..config import APP_NAME, APP_VERSION, BUILD_NUMBER


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.resize(480, 400)

        layout = QVBoxLayout(self)

        title_lbl = QLabel(f"<h2>{APP_NAME} v{APP_VERSION} (Build {BUILD_NUMBER})</h2>", self)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        desc_lbl = QLabel("GRBL CNC Controller with Heightmap Auto-Leveling and 3D Visualizer.<br>"
                          "Rewritten in Python / PyQt6 / PyOpenGL.", self)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_lbl)

        txt_license = QTextEdit(self)
        txt_license.setReadOnly(True)
        txt_license.setPlainText(
            "Candle GRBL Controller - Enhanced Python Edition\n"
            "Copyright (C) 2015-2025 Hayrullin Denis Ravilevich\n"
            "Python Edition Copyright (C) 2026\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files (the 'Software'), to deal "
            "in the Software without restriction, including without limitation the rights "
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
            "copies of the Software, and to permit persons to whom the Software is "
            "furnished to do so, subject to the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be included in "
            "all copies or substantial portions of the Software."
        )
        layout.addWidget(txt_license)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)

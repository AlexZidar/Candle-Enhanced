"""Candle Documentation and Reference Viewer."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox
)


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Candle Help & Documentation")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml("""
        <h1>Candle GRBL Controller - Help & Reference</h1>
        <hr>
        <h3>Navigation & Controls</h3>
        <ul>
            <li><b>Left Click + Drag</b> in 3D Visualizer: Rotate / Orbit 3D camera.</li>
            <li><b>Right Click / Middle Click + Drag</b>: Pan 3D viewport.</li>
            <li><b>Mouse Wheel</b>: Zoom in / Zoom out.</li>
            <li><b>Double Click</b>: Center view and reset pan.</li>
        </ul>
        <hr>
        <h3>Keyboard Jogging Shortcuts (When Keyboard Control is Checked)</h3>
        <ul>
            <li><b>Left / Right Arrow</b>: Jog X- / X+</li>
            <li><b>Up / Down Arrow</b>: Jog Y+ / Y-</li>
            <li><b>Page Up / Page Down</b>: Jog Z+ / Z-</li>
            <li><b>Insert / Delete</b>: Jog A+ / A-</li>
            <li><b>Shift + Movement Key</b>: Continuous jog while key held.</li>
        </ul>
        <hr>
        <h3>Heightmap & Auto-Leveling</h3>
        <ol>
            <li>Configure your work bounds (Border X, Y, Width, Height) in the Heightmap panel.</li>
            <li>Select grid probe density (Grid X, Grid Y, Z-top, Z-bottom, Probe feed).</li>
            <li>Click <b>Probe</b> to automatically measure surface height at all grid points.</li>
            <li>Check <b>Use heightmap</b> to dynamically deform the loaded G-code file with bicubic interpolated Z-elevation offsets during execution.</li>
        </ol>
        <hr>
        <h3>Overrides & Real-Time Controls</h3>
        <ul>
            <li><b>Feed Rate Override</b>: +10%, -10%, +1%, -1%, 100% Reset.</li>
            <li><b>Rapid Rate Override</b>: 100%, 50%, 25%.</li>
            <li><b>Spindle Speed Override</b>: +10%, -10%, +1%, -1%, 100% Reset.</li>
            <li><b>Realtime Buttons</b>: Pause (~ / !), Reset (Ctrl+X / 0x18), Unlock ($X), Home ($H), Check ($C), Sleep ($SLP).</li>
        </ul>
        """)
        layout.addWidget(self.browser)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        btn_box.rejected.connect(self.accept)
        layout.addWidget(btn_box)

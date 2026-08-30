"""Pre-run Safety Checklist Dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QCheckBox, QLabel, QDialogButtonBox
)


class ChecklistDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pre-Job Safety Checklist")
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        lbl = QLabel("<b>Please verify the following safety checks before starting job:</b>", self)
        layout.addWidget(lbl)

        self.checks = [
            QCheckBox("Workpiece is securely clamped to the wasteboard.", self),
            QCheckBox("Appropriate tool bit is installed and collet is tightened.", self),
            QCheckBox("Work coordinate origin (XYZ zero) is correctly set.", self),
            QCheckBox("Z clearance / Safe Z is unobstructed across travel paths.", self),
            QCheckBox("Spindle speed / RPM and feed rates are verified.", self),
            QCheckBox("Dust extraction and safety glasses are in place.", self),
        ]

        for chk in self.checks:
            chk.toggled.connect(self._on_check_toggled)
            layout.addWidget(chk)

        layout.addStretch()

        self.btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self
        )
        self.btn_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        layout.addWidget(self.btn_box)

    def _on_check_toggled(self):
        all_checked = all(c.isChecked() for c in self.checks)
        self.btn_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(all_checked)

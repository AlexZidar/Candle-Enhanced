"""Full Settings and Preferences Dialog for Candle."""

from typing import Dict, Any
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLineEdit, QTextEdit, QPushButton, QDialogButtonBox,
    QGroupBox, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QColor
from .storage import SettingsStorage
from .profile_manager import ProfileManager
from ..connection.serial_conn import SerialPortConnection
from ..widgets.color_picker import ColorPickerButton
from ..config import ConnectionType


class SettingsDialog(QDialog):
    def __init__(self, storage: SettingsStorage, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(600, 520)

        self.m_storage = storage
        self.m_profileManager = profile_manager

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        main_layout.addWidget(self.tabs)

        self._create_connection_tab()
        self._create_visualizer_tab()
        self._create_control_tab()
        self._create_parser_tab()
        self._create_profiles_tab()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Apply,
            self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.applySettings)
        main_layout.addWidget(self.button_box)

        self.loadSettings()

    def _create_connection_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_conn = QGroupBox("Connection Settings", tab)
        form = QFormLayout(grp_conn)

        self.cboConnType = QComboBox(tab)
        self.cboConnType.addItems(["Serial Port", "Telnet", "WebSocket"])
        self.cboConnType.currentIndexChanged.connect(self._on_conn_type_changed)
        form.addRow("Type:", self.cboConnType)

        # Serial
        self.port_layout = QHBoxLayout()
        self.cboPort = QComboBox(tab)
        self.cboPort.setEditable(True)
        self.btnRefreshPorts = QPushButton("Refresh", tab)
        self.btnRefreshPorts.clicked.connect(self.refreshPorts)
        self.port_layout.addWidget(self.cboPort)
        self.port_layout.addWidget(self.btnRefreshPorts)
        form.addRow("Port:", self.port_layout)

        self.cboBaud = QComboBox(tab)
        self.cboBaud.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "250000", "500000"])
        form.addRow("Baud Rate:", self.cboBaud)

        # Telnet
        self.txtTelnetAddress = QLineEdit("192.168.1.100", tab)
        form.addRow("Telnet Address:", self.txtTelnetAddress)
        self.txtTelnetPort = QSpinBox(tab)
        self.txtTelnetPort.setRange(1, 65535)
        self.txtTelnetPort.setValue(23)
        form.addRow("Telnet Port:", self.txtTelnetPort)

        # WebSocket
        self.txtWebSocketUrl = QLineEdit("ws://192.168.1.100:81", tab)
        form.addRow("WebSocket URL:", self.txtWebSocketUrl)
        self.chkWebSocketBinary = QCheckBox("Binary WebSocket Frame", tab)
        form.addRow("", self.chkWebSocketBinary)

        self.chkResetOnConn = QCheckBox("Soft reset upon connection", tab)
        form.addRow("", self.chkResetOnConn)

        layout.addWidget(grp_conn)
        layout.addStretch()
        self.tabs.addTab(tab, "Connection")
        self.refreshPorts()

    def _create_visualizer_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Render options
        grp_render = QGroupBox("Rendering", tab)
        form_r = QFormLayout(grp_render)

        self.chkAntialiasing = QCheckBox("Antialiasing (Smooth lines)", tab)
        form_r.addRow(self.chkAntialiasing)
        self.chkMsaa = QCheckBox("Multisample Anti-Aliasing (MSAA 8x)", tab)
        form_r.addRow(self.chkMsaa)
        self.chkZBuffer = QCheckBox("Z-Buffer depth test", tab)
        form_r.addRow(self.chkZBuffer)
        self.chkPerspective = QCheckBox("Perspective projection", tab)
        form_r.addRow(self.chkPerspective)

        self.spnFps = QSpinBox(tab)
        self.spnFps.setRange(10, 144)
        self.spnFps.setValue(60)
        form_r.addRow("Target FPS:", self.spnFps)

        self.spnLineWidth = QDoubleSpinBox(tab)
        self.spnLineWidth.setRange(0.5, 10.0)
        self.spnLineWidth.setValue(1.0)
        form_r.addRow("Line Width:", self.spnLineWidth)

        self.spnPointSize = QDoubleSpinBox(tab)
        self.spnPointSize.setRange(1.0, 20.0)
        self.spnPointSize.setValue(4.0)
        form_r.addRow("Point Size:", self.spnPointSize)

        layout.addWidget(grp_render)

        # Colors
        grp_colors = QGroupBox("Colors", tab)
        form_c = QFormLayout(grp_colors)

        self.btnColorBackground = ColorPickerButton(QColor("#1e1e1e"), tab)
        form_c.addRow("Background:", self.btnColorBackground)
        self.btnColorText = ColorPickerButton(QColor("#ffffff"), tab)
        form_c.addRow("HUD Text:", self.btnColorText)
        self.btnColorNormal = ColorPickerButton(QColor("#4d90fe"), tab)
        form_c.addRow("Toolpath (Normal):", self.btnColorNormal)
        self.btnColorHighlight = ColorPickerButton(QColor("#ffff00"), tab)
        form_c.addRow("Highlight:", self.btnColorHighlight)
        self.btnColorZMovement = ColorPickerButton(QColor("#ff3333"), tab)
        form_c.addRow("Z Movement:", self.btnColorZMovement)
        self.btnColorDrawn = ColorPickerButton(QColor("#888888"), tab)
        form_c.addRow("Drawn Path:", self.btnColorDrawn)

        layout.addWidget(grp_colors)
        layout.addStretch()
        self.tabs.addTab(tab, "Visualizer")

    def _create_control_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_ctrl = QGroupBox("Machine & Motion", tab)
        form = QFormLayout(grp_ctrl)

        self.spnSafeZ = QDoubleSpinBox(tab)
        self.spnSafeZ.setRange(-100.0, 100.0)
        self.spnSafeZ.setValue(5.0)
        form.addRow("Work Safe Z (mm):", self.spnSafeZ)

        self.chkSafeTravel = QCheckBox("Enable Safe Travel (Pre/Post Job Top Clearance)", tab)
        form.addRow(self.chkSafeTravel)

        self.spnSafeTravelClearance = QDoubleSpinBox(tab)
        self.spnSafeTravelClearance.setRange(0.5, 50.0)
        self.spnSafeTravelClearance.setValue(3.0)
        form.addRow("Top Limit Clearance (G53 Z -mm):", self.spnSafeTravelClearance)

        self.spnRapidSpeed = QSpinBox(tab)
        self.spnRapidSpeed.setRange(1, 20000)
        self.spnRapidSpeed.setValue(1000)
        form.addRow("Rapid Feed (G0 mm/min):", self.spnRapidSpeed)

        self.spnAcceleration = QSpinBox(tab)
        self.spnAcceleration.setRange(1, 10000)
        self.spnAcceleration.setValue(400)
        form.addRow("Acceleration (mm/s²):", self.spnAcceleration)

        self.spnQueryInterval = QSpinBox(tab)
        self.spnQueryInterval.setRange(50, 2000)
        self.spnQueryInterval.setValue(200)
        form.addRow("Status Query Interval (ms):", self.spnQueryInterval)

        # Machine Bounds
        bounds_layout = QHBoxLayout()
        self.spnBoundX = QDoubleSpinBox(tab)
        self.spnBoundX.setRange(10, 5000)
        self.spnBoundX.setValue(300)
        self.spnBoundY = QDoubleSpinBox(tab)
        self.spnBoundY.setRange(10, 5000)
        self.spnBoundY.setValue(180)
        self.spnBoundZ = QDoubleSpinBox(tab)
        self.spnBoundZ.setRange(5, 1000)
        self.spnBoundZ.setValue(45)
        bounds_layout.addWidget(QLabel("X:"))
        bounds_layout.addWidget(self.spnBoundX)
        bounds_layout.addWidget(QLabel("Y:"))
        bounds_layout.addWidget(self.spnBoundY)
        bounds_layout.addWidget(QLabel("Z:"))
        bounds_layout.addWidget(self.spnBoundZ)
        form.addRow("Work Area (mm):", bounds_layout)

        # Spindle / Laser
        self.spnSpindleMin = QSpinBox(tab)
        self.spnSpindleMin.setRange(0, 100000)
        self.spnSpindleMax = QSpinBox(tab)
        self.spnSpindleMax.setRange(1, 100000)
        self.spnSpindleMax.setValue(10000)
        spin_layout = QHBoxLayout()
        spin_layout.addWidget(QLabel("Min:"))
        spin_layout.addWidget(self.spnSpindleMin)
        spin_layout.addWidget(QLabel("Max:"))
        spin_layout.addWidget(self.spnSpindleMax)
        form.addRow("Spindle RPM:", spin_layout)

        layout.addWidget(grp_ctrl)
        layout.addStretch()
        self.tabs.addTab(tab, "Control")

    def _create_parser_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_p = QGroupBox("G-Code Parser & Preprocessor", tab)
        form = QFormLayout(grp_p)

        self.chkRemoveWhitespace = QCheckBox("Remove whitespace in commands", tab)
        form.addRow(self.chkRemoveWhitespace)

        self.chkConvertArcs = QCheckBox("Convert arcs (G2/G3) to linear lines (G1)", tab)
        form.addRow(self.chkConvertArcs)

        self.spnArcLength = QDoubleSpinBox(tab)
        self.spnArcLength.setRange(0.01, 10.0)
        self.spnArcLength.setValue(0.3)
        form.addRow("Arc Segment Length (mm):", self.spnArcLength)

        self.spnTruncateDecimals = QSpinBox(tab)
        self.spnTruncateDecimals.setRange(1, 8)
        self.spnTruncateDecimals.setValue(4)
        form.addRow("Decimal Precision:", self.spnTruncateDecimals)

        layout.addWidget(grp_p)
        layout.addStretch()
        self.tabs.addTab(tab, "Parser")

    def _create_profiles_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp = QGroupBox("Machine Profiles", tab)
        form = QFormLayout(grp)

        self.cboProfiles = QComboBox(tab)
        self.cboProfiles.addItems(self.m_profileManager.profiles())
        form.addRow("Profile:", self.cboProfiles)

        btn_row = QHBoxLayout()
        self.btnSaveProfile = QPushButton("Save Profile", tab)
        self.btnSaveProfile.clicked.connect(self._on_save_profile)
        self.btnDeleteProfile = QPushButton("Delete Profile", tab)
        self.btnDeleteProfile.clicked.connect(self._on_delete_profile)
        btn_row.addWidget(self.btnSaveProfile)
        btn_row.addWidget(self.btnDeleteProfile)
        form.addRow("", btn_row)

        btn_io = QHBoxLayout()
        self.btnExportProfile = QPushButton("Export JSON...", tab)
        self.btnExportProfile.clicked.connect(self._on_export_profile)
        self.btnImportProfile = QPushButton("Import JSON...", tab)
        self.btnImportProfile.clicked.connect(self._on_import_profile)
        btn_io.addWidget(self.btnExportProfile)
        btn_io.addWidget(self.btnImportProfile)
        form.addRow("File:", btn_io)

        layout.addWidget(grp)
        layout.addStretch()
        self.tabs.addTab(tab, "Profiles")

    def _on_conn_type_changed(self, idx: int):
        is_serial = (idx == int(ConnectionType.Serial))
        is_telnet = (idx == int(ConnectionType.Telnet))
        is_ws = (idx == int(ConnectionType.WebSocket))

        self.cboPort.setEnabled(is_serial)
        self.btnRefreshPorts.setEnabled(is_serial)
        self.cboBaud.setEnabled(is_serial)
        self.txtTelnetAddress.setEnabled(is_telnet)
        self.txtTelnetPort.setEnabled(is_telnet)
        self.txtWebSocketUrl.setEnabled(is_ws)
        self.chkWebSocketBinary.setEnabled(is_ws)

    def refreshPorts(self):
        cur = self.cboPort.currentText()
        self.cboPort.clear()
        ports = SerialPortConnection.availablePorts()
        self.cboPort.addItems(ports)
        if cur and cur in ports:
            self.cboPort.setCurrentText(cur)

    def loadSettings(self):
        s = self.m_storage
        self.cboConnType.setCurrentIndex(s.get("Connection/type", int(ConnectionType.Serial)))
        self.cboPort.setCurrentText(str(s.get("Connection/port", "")))
        self.cboBaud.setCurrentText(str(s.get("Connection/baud", 115200)))
        self.txtTelnetAddress.setText(str(s.get("Connection/telnetAddress", "192.168.1.100")))
        self.txtTelnetPort.setValue(int(s.get("Connection/telnetPort", 23)))
        self.txtWebSocketUrl.setText(str(s.get("Connection/webSocketUrl", "ws://192.168.1.100:81")))
        self.chkWebSocketBinary.setChecked(bool(s.get("Connection/webSocketBinary", False)))
        self.chkResetOnConn.setChecked(bool(s.get("Connection/resetOnConnection", True)))

        self.chkAntialiasing.setChecked(bool(s.get("Visualizer/antialiasing", True)))
        self.chkMsaa.setChecked(bool(s.get("Visualizer/msaa", False)))
        self.chkZBuffer.setChecked(bool(s.get("Visualizer/zBuffer", True)))
        self.chkPerspective.setChecked(bool(s.get("Visualizer/perspective", False)))
        self.spnFps.setValue(int(s.get("Visualizer/fps", 60)))
        self.spnLineWidth.setValue(float(s.get("Visualizer/lineWidth", 1.0)))
        self.spnPointSize.setValue(float(s.get("Visualizer/pointSize", 4.0)))

        self.btnColorBackground.setColor(QColor(str(s.get("Visualizer/colorBackground", "#1e1e1e"))))
        self.btnColorText.setColor(QColor(str(s.get("Visualizer/colorText", "#ffffff"))))
        self.btnColorNormal.setColor(QColor(str(s.get("Visualizer/colorNormal", "#4d90fe"))))
        self.btnColorHighlight.setColor(QColor(str(s.get("Visualizer/colorHighlight", "#ffff00"))))
        self.btnColorZMovement.setColor(QColor(str(s.get("Visualizer/colorZMovement", "#ff3333"))))
        self.btnColorDrawn.setColor(QColor(str(s.get("Visualizer/colorDrawn", "#888888"))))

        self.spnSafeZ.setValue(float(s.get("Control/safeZ", 5.0)))
        self.chkSafeTravel.setChecked(bool(s.get("Control/safeTravel", True)))
        self.spnSafeTravelClearance.setValue(float(s.get("Control/safeTravelClearance", 3.0)))
        self.spnRapidSpeed.setValue(int(s.get("Control/rapidSpeed", 1000)))
        self.spnAcceleration.setValue(int(s.get("Control/acceleration", 400)))
        self.spnQueryInterval.setValue(int(s.get("Control/queryStateTime", 200)))
        self.spnBoundX.setValue(float(s.get("Control/machineBoundsX", 300.0)))
        self.spnBoundY.setValue(float(s.get("Control/machineBoundsY", 180.0)))
        self.spnBoundZ.setValue(float(s.get("Control/machineBoundsZ", 45.0)))
        self.spnSpindleMin.setValue(int(s.get("Control/spindleSpeedMin", 0)))
        self.spnSpindleMax.setValue(int(s.get("Control/spindleSpeedMax", 10000)))

        self.chkRemoveWhitespace.setChecked(bool(s.get("Parser/removeAllWhitespace", True)))
        self.chkConvertArcs.setChecked(bool(s.get("Parser/convertArcsToLines", False)))
        self.spnArcLength.setValue(float(s.get("Visualizer/arcLength", 0.3)))
        self.spnTruncateDecimals.setValue(int(s.get("Parser/truncateDecimalLength", 4)))

    def applySettings(self):
        s = self.m_storage
        s.set("Connection/type", self.cboConnType.currentIndex())
        s.set("Connection/port", self.cboPort.currentText())
        s.set("Connection/baud", int(self.cboBaud.currentText() or 115200))
        s.set("Connection/telnetAddress", self.txtTelnetAddress.text())
        s.set("Connection/telnetPort", self.txtTelnetPort.value())
        s.set("Connection/webSocketUrl", self.txtWebSocketUrl.text())
        s.set("Connection/webSocketBinary", self.chkWebSocketBinary.isChecked())
        s.set("Connection/resetOnConnection", self.chkResetOnConn.isChecked())

        s.set("Visualizer/antialiasing", self.chkAntialiasing.isChecked())
        s.set("Visualizer/msaa", self.chkMsaa.isChecked())
        s.set("Visualizer/zBuffer", self.chkZBuffer.isChecked())
        s.set("Visualizer/perspective", self.chkPerspective.isChecked())
        s.set("Visualizer/fps", self.spnFps.value())
        s.set("Visualizer/lineWidth", self.spnLineWidth.value())
        s.set("Visualizer/pointSize", self.spnPointSize.value())

        s.set("Visualizer/colorBackground", self.btnColorBackground.color().name())
        s.set("Visualizer/colorText", self.btnColorText.color().name())
        s.set("Visualizer/colorNormal", self.btnColorNormal.color().name())
        s.set("Visualizer/colorHighlight", self.btnColorHighlight.color().name())
        s.set("Visualizer/colorZMovement", self.btnColorZMovement.color().name())
        s.set("Visualizer/colorDrawn", self.btnColorDrawn.color().name())

        s.set("Control/safeZ", self.spnSafeZ.value())
        s.set("Control/safeTravel", self.chkSafeTravel.isChecked())
        s.set("Control/safeTravelClearance", self.spnSafeTravelClearance.value())
        s.set("Control/rapidSpeed", self.spnRapidSpeed.value())
        s.set("Control/acceleration", self.spnAcceleration.value())
        s.set("Control/queryStateTime", self.spnQueryInterval.value())
        s.set("Control/machineBoundsX", self.spnBoundX.value())
        s.set("Control/machineBoundsY", self.spnBoundY.value())
        s.set("Control/machineBoundsZ", self.spnBoundZ.value())
        s.set("Control/spindleSpeedMin", self.spnSpindleMin.value())
        s.set("Control/spindleSpeedMax", self.spnSpindleMax.value())

        s.set("Parser/removeAllWhitespace", self.chkRemoveWhitespace.isChecked())
        s.set("Parser/convertArcsToLines", self.chkConvertArcs.isChecked())
        s.set("Visualizer/arcLength", self.spnArcLength.value())
        s.set("Parser/truncateDecimalLength", self.spnTruncateDecimals.value())

        s.sync()

    def accept(self):
        self.applySettings()
        super().accept()

    def _on_save_profile(self):
        name = self.cboProfiles.currentText().strip()
        if not name:
            return
        self.applySettings()
        self.m_profileManager.saveProfile(name, self.m_storage.m_cache)
        QMessageBox.information(self, "Profile Saved", f"Profile '{name}' saved successfully.")

    def _on_delete_profile(self):
        name = self.cboProfiles.currentText()
        if name == "Default":
            QMessageBox.warning(self, "Warning", "Cannot delete Default profile.")
            return
        if self.m_profileManager.deleteProfile(name):
            self.cboProfiles.removeItem(self.cboProfiles.currentIndex())
            QMessageBox.information(self, "Profile Deleted", f"Profile '{name}' deleted.")

    def _on_export_profile(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Export Settings", "candle_settings.json", "JSON Files (*.json)")
        if fname:
            self.applySettings()
            self.m_storage.exportToJson(fname)

    def _on_import_profile(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "JSON Files (*.json)")
        if fname:
            if self.m_storage.importFromJson(fname):
                self.loadSettings()
                QMessageBox.information(self, "Imported", "Settings imported successfully.")

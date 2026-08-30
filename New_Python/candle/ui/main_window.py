"""Candle Main Window and GRBL Controller Implementation."""

import os
import re
import math
import time
from typing import List, Optional, Dict, Tuple
from PyQt6.QtCore import Qt, QTimer, QTime, QPoint, QRectF, QSize, pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSplitter, QDockWidget, QTableView, QSlider, QPushButton,
    QLabel, QLineEdit, QTextEdit, QCheckBox, QRadioButton, QButtonGroup,
    QComboBox, QSpinBox, QDoubleSpinBox, QToolBar, QMenuBar, QMenu,
    QStatusBar, QFileDialog, QMessageBox, QHeaderView, QAbstractItemView,
    QGroupBox, QSizePolicy, QStyle, QScrollArea, QFrame
)
from PyQt6.QtGui import QIcon, QColor, QFont, QAction, QVector3D, QKeySequence

from ..config import (
    APP_NAME, APP_VERSION, ConnectionType, SenderState, DeviceState,
    DEVICE_STATUS_STRINGS, STATUS_CAPTIONS, STATUS_BACK_COLORS, STATUS_FORE_COLORS,
    GCodeItemState, DrawMode, SplineType, BUFFER_LENGTH, RECENT_FILES_COUNT
)
from ..settings.storage import SettingsStorage
from ..settings.profile_manager import ProfileManager
from ..settings.settings_dialog import SettingsDialog
from ..connection.base import Connection
from ..connection.serial_conn import SerialPortConnection
from ..connection.telnet_conn import TelnetConnection
from ..connection.websocket_conn import WebSocketConnection
from ..parser.gcode_parser import GcodeParser
from ..parser.gcode_view_parser import GcodeViewParse
from ..kinematics.time_estimator import TimeEstimator
from ..heightmap.heightmap_model import HeightMapTableModel
from ..heightmap.heightmap_manager import HeightMapManager, HeightMapData
from ..models.gcode_table_model import GCodeTableModel, GCodeItem
from ..models.table_history import TableHistoryManager
from ..drawers.gcode_drawer import GcodeDrawer
from ..drawers.tool_drawer import ToolDrawer
from ..drawers.origin_drawer import OriginDrawer
from ..drawers.selection_drawer import SelectionDrawer
from ..drawers.machine_bounds_drawer import MachineBoundsDrawer
from ..drawers.heightmap_border_drawer import HeightMapBorderDrawer
from ..drawers.heightmap_grid_drawer import HeightMapGridDrawer
from ..drawers.heightmap_interpolation_drawer import HeightMapInterpolationDrawer
from ..widgets.gl_widget import GLWidget
from ..widgets.slider_box import SliderBox
from ..widgets.styled_tool_button import StyledToolButton
from ..widgets.combo_box import ComboBoxKey
from ..widgets.no_wheel_filter import NoWheelEventFilter
from ..models.macro_model import Macro, MacroBlock, BlockType, MacroManager
from ..kinematics.macro_runner import MacroRunner
from .about_dialog import AboutDialog
from .help_dialog import HelpDialog
from .checklist_dialog import ChecklistDialog
from .script_widget import ScriptWidget
from .log_widget import LogWidget
from .macro_builder_dialog import MacroBuilderDialog


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - GRBL Controller")
        self.resize(1280, 800)

        # Core Subsystems
        self.m_storage = SettingsStorage()
        self.m_profileManager = ProfileManager()
        self.m_connection: Optional[Connection] = None

        self.m_parser = GcodeParser()
        self.m_viewParser = GcodeViewParse()
        self.m_probeParser = GcodeParser()
        self.m_probeViewParser = GcodeViewParse()

        self.m_programModel = GCodeTableModel(self)
        self.m_probeModel = GCodeTableModel(self)
        self.m_currentModel = self.m_programModel
        self.m_heightMapModel = HeightMapTableModel(self)

        self.m_programTableHistory = TableHistoryManager(self.m_programModel, self)

        # GRBL Communication State
        self.m_senderState: SenderState = SenderState.Stopped
        self.m_deviceState: DeviceState = DeviceState.Unknown
        self.m_queue: List[str] = []
        self.m_queueCommandIndex: int = 0
        self.m_bufferLength: List[int] = []  # length of commands sent and awaiting ok/error
        self.m_statusQueryTimer = QTimer(self)
        self.m_statusQueryTimer.timeout.connect(self._query_status)

        self.m_mpos: QVector3D = QVector3D(0, 0, 0)
        self.m_wpos: QVector3D = QVector3D(0, 0, 0)
        self.m_wco: QVector3D = QVector3D(0, 0, 0)
        self.m_axisA_mpos: float = 0.0
        self.m_axisA_wpos: float = 0.0

        self.m_programFileName: str = ""
        self.m_heightMapFileName: str = ""
        self.m_isProbing: bool = False
        self.m_probeIndex: int = 0

        self.m_startTime: float = 0.0
        self.m_elapsedTimer = QTimer(self)
        self.m_elapsedTimer.timeout.connect(self._update_elapsed_time)

        # Jog Tracking & Graceful Limit Recovery
        self.m_lastJogAxis: str = "Z"
        self.m_lastJogDirection: int = 1
        self.m_lastJogTime: float = 0.0
        self.m_isRecoveringFromLimit: bool = False

        # Touch Plate Z-Probe Zeroing State
        self.m_isZeroProbing: bool = False
        self.m_zeroProbeStage: int = 0

        # Custom Macros & Command Chains Subsystem
        self.m_macroManager = MacroManager(self.m_storage)
        self.m_macroRunner = MacroRunner(self, self)
        self.m_noWheelFilter = NoWheelEventFilter(self)

        # Initialize Drawers
        self.m_codeDrawer = GcodeDrawer()
        self.m_probeCodeDrawer = GcodeDrawer()
        self.m_toolDrawer = ToolDrawer()
        self.m_originDrawer = OriginDrawer()
        self.m_selectionDrawer = SelectionDrawer()
        self.m_boundsDrawer = MachineBoundsDrawer()
        self.m_heightMapBorderDrawer = HeightMapBorderDrawer()
        self.m_heightMapGridDrawer = HeightMapGridDrawer()
        self.m_heightMapInterpolationDrawer = HeightMapInterpolationDrawer()

        self.m_codeDrawer.setViewParser(self.m_viewParser)
        self.m_probeCodeDrawer.setViewParser(self.m_probeViewParser)
        self.m_heightMapGridDrawer.setModel(self.m_heightMapModel)

        # Build GUI
        self._build_ui()
        self._build_menus()
        self._setup_connection()
        self._apply_settings()

        # Install no-wheel filter on scrollable docks
        self._install_no_wheel_filter(self.dockDevice)
        self._install_no_wheel_filter(self.dockModification)

        # Keyboard event filter for jogging
        self.installEventFilter(self)

    def _install_no_wheel_filter(self, widget: QWidget):
        if isinstance(widget, (QSlider, QSpinBox, QDoubleSpinBox, QComboBox)):
            widget.installEventFilter(self.m_noWheelFilter)
        for child in widget.findChildren((QSlider, QSpinBox, QDoubleSpinBox, QComboBox)):
            child.installEventFilter(self.m_noWheelFilter)

    def _build_ui(self):
        # Central Widget: G-Code Program Table & Stream Controls
        central = QWidget(self)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(4, 4, 4, 4)

        # Table
        self.tblProgram = QTableView(central)
        self.tblProgram.setModel(self.m_programModel)
        self.tblProgram.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tblProgram.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tblProgram.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tblProgram.selectionModel().currentRowChanged.connect(self._on_table_row_changed)
        central_layout.addWidget(self.tblProgram)

        # Progress slider & Info
        slider_row = QHBoxLayout()
        self.sliProgram = QSlider(Qt.Orientation.Horizontal, central)
        self.sliProgram.setRange(0, 0)
        self.sliProgram.sliderMoved.connect(self._on_slider_moved)
        self.lblProgramProgress = QLabel("0 / 0", central)
        slider_row.addWidget(self.sliProgram)
        slider_row.addWidget(self.lblProgramProgress)
        central_layout.addLayout(slider_row)

        # Bottom Action Bar
        btn_bar = QHBoxLayout()
        self.btnSend = QPushButton("Send", central)
        self.btnSend.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white; min-height: 28px;")
        self.btnSend.clicked.connect(self.startStreaming)

        self.btnPause = QPushButton("Pause", central)
        self.btnPause.clicked.connect(self.pauseStreaming)

        self.btnAbort = QPushButton("Abort", central)
        self.btnAbort.setStyleSheet("background-color: #c62828; color: white;")
        self.btnAbort.clicked.connect(self.abortStreaming)

        self.btnReset = QPushButton("Reset", central)
        self.btnReset.clicked.connect(self.resetDevice)

        self.btnCheck = QPushButton("Check", central)
        self.btnCheck.clicked.connect(self.checkMode)

        self.chkAutoScroll = QCheckBox("Auto-scroll", central)
        self.chkAutoScroll.setChecked(True)

        self.chkSafeTravel = QCheckBox("Safe Travel (Top Clearance)", central)
        self.chkSafeTravel.setToolTip("Lifts spindle to top limit clearance (G53 Z-3mm) before moving, and retracts & stops spindle after job completion.")
        self.chkSafeTravel.setChecked(bool(self.m_storage.get("Control/safeTravel", True)))
        self.chkSafeTravel.toggled.connect(lambda v: self.m_storage.set("Control/safeTravel", v))

        btn_bar.addWidget(self.btnSend)
        btn_bar.addWidget(self.btnPause)
        btn_bar.addWidget(self.btnAbort)
        btn_bar.addWidget(self.btnReset)
        btn_bar.addWidget(self.btnCheck)
        btn_bar.addWidget(self.chkAutoScroll)
        btn_bar.addWidget(self.chkSafeTravel)
        btn_bar.addStretch()

        central_layout.addLayout(btn_bar)
        self.setCentralWidget(central)

        # Enable dock nesting and animation
        self.setDockNestingEnabled(True)
        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AnimatedDocks)

        # Build Docks
        self._build_visualizer_dock()
        self._build_device_dock()
        self._build_heightmap_dock()
        self._build_console_dock()
        self._build_user_dock()
        self._build_script_dock()
        self._build_log_dock()

        # Place & Tabify Docks
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockDevice)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockModification)
        self.tabifyDockWidget(self.dockDevice, self.dockModification)
        self.dockDevice.raise_()

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockVisualizer)

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockConsole)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockUser)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockScript)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockLog)
        self.tabifyDockWidget(self.dockConsole, self.dockUser)
        self.tabifyDockWidget(self.dockUser, self.dockScript)
        self.tabifyDockWidget(self.dockScript, self.dockLog)
        self.dockConsole.raise_()

        self.resizeDocks([self.dockDevice, self.dockModification], [300, 300], Qt.Orientation.Horizontal)
        self.resizeDocks([self.dockVisualizer], [650], Qt.Orientation.Horizontal)
        self.resizeDocks([self.dockConsole], [160], Qt.Orientation.Vertical)

    def _build_visualizer_dock(self):
        self.dockVisualizer = QDockWidget("3D Visualizer", self)
        self.dockVisualizer.setObjectName("dockVisualizer")
        wgt = QWidget(self.dockVisualizer)
        layout = QVBoxLayout(wgt)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Controls bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 4, 4, 4)
        self.btnViewTop = QPushButton("Top", wgt)
        self.btnViewTop.clicked.connect(lambda: self.glwVisualizer.topView())
        self.btnViewFront = QPushButton("Front", wgt)
        self.btnViewFront.clicked.connect(lambda: self.glwVisualizer.frontView())
        self.btnViewLeft = QPushButton("Left", wgt)
        self.btnViewLeft.clicked.connect(lambda: self.glwVisualizer.leftView())
        self.btnViewIso = QPushButton("Iso", wgt)
        self.btnViewIso.clicked.connect(lambda: self.glwVisualizer.isometricView())
        self.btnViewFit = QPushButton("Fit", wgt)
        self.btnViewFit.clicked.connect(lambda: self.glwVisualizer.fitDrawable(self.m_codeDrawer))

        self.chkPerspective = QCheckBox("Perspective", wgt)
        self.chkPerspective.toggled.connect(lambda p: self.glwVisualizer.setPerspective(p))

        top_bar.addWidget(self.btnViewTop)
        top_bar.addWidget(self.btnViewFront)
        top_bar.addWidget(self.btnViewLeft)
        top_bar.addWidget(self.btnViewIso)
        top_bar.addWidget(self.btnViewFit)
        top_bar.addWidget(self.chkPerspective)
        top_bar.addStretch()

        layout.addLayout(top_bar)

        # 3D Viewport
        self.glwVisualizer = GLWidget(wgt)
        self.glwVisualizer.addDrawable(self.m_boundsDrawer)
        self.glwVisualizer.addDrawable(self.m_originDrawer)
        self.glwVisualizer.addDrawable(self.m_codeDrawer)
        self.glwVisualizer.addDrawable(self.m_toolDrawer)
        self.glwVisualizer.addDrawable(self.m_selectionDrawer)
        self.glwVisualizer.addDrawable(self.m_heightMapBorderDrawer)
        self.glwVisualizer.addDrawable(self.m_heightMapGridDrawer)
        self.glwVisualizer.addDrawable(self.m_heightMapInterpolationDrawer)

        layout.addWidget(self.glwVisualizer)
        self.dockVisualizer.setWidget(wgt)

    def _build_device_dock(self):
        self.dockDevice = QDockWidget("Device / Controls", self)
        self.dockDevice.setObjectName("dockDevice")
        self.dockDevice.setMinimumWidth(280)

        scroll = QScrollArea(self.dockDevice)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        wgt = QWidget(scroll)
        layout = QVBoxLayout(wgt)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Connection Header
        conn_row = QHBoxLayout()
        self.lblConnInfo = QLabel("Not Connected", wgt)
        self.lblConnInfo.setStyleSheet("color: #aaaaaa; font-size: 11px; font-weight: bold;")
        self.btnConnectToggle = QPushButton("Connect", wgt)
        self.btnConnectToggle.setFixedHeight(24)
        self.btnConnectToggle.clicked.connect(self._toggle_connection)
        
        self.btnReconnect = QPushButton("↻", wgt)
        self.btnReconnect.setFixedSize(24, 24)
        self.btnReconnect.setToolTip("Reconnect to Controller")
        self.btnReconnect.clicked.connect(self._setup_connection)

        conn_row.addWidget(self.lblConnInfo, stretch=1)
        conn_row.addWidget(self.btnConnectToggle)
        conn_row.addWidget(self.btnReconnect)
        layout.addLayout(conn_row)

        # Status Box
        self.lblState = QLabel("DISCONNECTED", wgt)
        self.lblState.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lblState.setFixedHeight(32)
        self.lblState.setStyleSheet(
            "font-weight: bold; font-size: 13px; background-color: #c62828; color: white; "
            "border-radius: 4px; padding: 4px;"
        )
        layout.addWidget(self.lblState)

        # Coordinates Panel
        grp_coord = QGroupBox("Coordinates", wgt)
        grid_coord = QGridLayout(grp_coord)
        grid_coord.setContentsMargins(6, 6, 6, 6)
        grid_coord.setSpacing(4)

        lbl_hdr_axis = QLabel("<b>Axis</b>", wgt); lbl_hdr_axis.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hdr_work = QLabel("<b>Work (WPos)</b>", wgt); lbl_hdr_work.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hdr_mach = QLabel("<b>Machine</b>", wgt); lbl_hdr_mach.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hdr_zero = QLabel("<b>Zero</b>", wgt); lbl_hdr_zero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hdr_ret = QLabel("<b>Ret</b>", wgt); lbl_hdr_ret.setAlignment(Qt.AlignmentFlag.AlignCenter)

        grid_coord.addWidget(lbl_hdr_axis, 0, 0)
        grid_coord.addWidget(lbl_hdr_work, 0, 1)
        grid_coord.addWidget(lbl_hdr_mach, 0, 2)
        grid_coord.addWidget(lbl_hdr_zero, 0, 3)
        grid_coord.addWidget(lbl_hdr_ret, 0, 4)

        self.lblWPosX = QLabel("0.000", wgt)
        self.lblWPosY = QLabel("0.000", wgt)
        self.lblWPosZ = QLabel("0.000", wgt)
        self.lblWPosA = QLabel("0.000", wgt)

        self.lblMPosX = QLabel("0.000", wgt)
        self.lblMPosY = QLabel("0.000", wgt)
        self.lblMPosZ = QLabel("0.000", wgt)
        self.lblMPosA = QLabel("0.000", wgt)

        for lbl in (self.lblWPosX, self.lblWPosY, self.lblWPosZ, self.lblWPosA,
                    self.lblMPosX, self.lblMPosY, self.lblMPosZ, self.lblMPosA):
            lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet(
                "background-color: rgba(0, 0, 0, 0.25); border: 1px solid #444; "
                "border-radius: 3px; padding: 2px 4px;"
            )
            lbl.setFixedHeight(24)
            lbl.setMinimumWidth(75)

        axes = [("X", self.lblWPosX, self.lblMPosX, "X"),
                ("Y", self.lblWPosY, self.lblMPosY, "Y"),
                ("Z", self.lblWPosZ, self.lblMPosZ, "Z"),
                ("A", self.lblWPosA, self.lblMPosA, "A")]

        for r, (axis_name, w_lbl, m_lbl, ax) in enumerate(axes, start=1):
            lbl_ax = QLabel(f"<b>{axis_name}</b>", wgt)
            lbl_ax.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid_coord.addWidget(lbl_ax, r, 0)
            grid_coord.addWidget(w_lbl, r, 1)
            grid_coord.addWidget(m_lbl, r, 2)

            btn_zero = QPushButton("0", wgt)
            btn_zero.setFixedSize(26, 24)
            btn_zero.setToolTip(f"Zero {ax} Axis (G92 {ax}0)")
            btn_zero.clicked.connect(lambda ch, a=ax: self.zeroAxis(a))
            grid_coord.addWidget(btn_zero, r, 3)

            btn_ret = QPushButton("↩", wgt)
            btn_ret.setFixedSize(26, 24)
            btn_ret.setToolTip(f"Return {ax} to Zero (G90 G0 {ax}0)")
            btn_ret.clicked.connect(lambda ch, a=ax: self.returnAxis(a))
            grid_coord.addWidget(btn_ret, r, 4)

        row_all = QHBoxLayout()
        btn_zero_all = QPushButton("Zero XYZ", wgt)
        btn_zero_all.setFixedHeight(26)
        btn_zero_all.clicked.connect(lambda: self.sendCommand("G92 X0 Y0 Z0"))
        
        self.btnProbeZ = QPushButton("🔍 Probe Z", wgt)
        self.btnProbeZ.setFixedHeight(26)
        self.btnProbeZ.setStyleSheet("font-weight: bold; background-color: #1565c0; color: white;")
        self.btnProbeZ.setToolTip("Auto Touch-Plate Z-Probe & Zero (G38.2 -> G92 Z{thickness})")
        self.btnProbeZ.clicked.connect(self.probeZeroZ)

        btn_safe_z = QPushButton("Safe Z", wgt)
        btn_safe_z.setFixedHeight(26)
        btn_safe_z.clicked.connect(self.moveToSafeZ)
        
        row_all.addWidget(btn_zero_all)
        row_all.addWidget(self.btnProbeZ)
        row_all.addWidget(btn_safe_z)

        layout.addWidget(grp_coord)
        layout.addLayout(row_all)

        # Machine Control Buttons
        grp_actions = QGroupBox("Commands", wgt)
        btn_grid = QGridLayout(grp_actions)
        btn_grid.setContentsMargins(6, 6, 6, 6)
        btn_grid.setSpacing(4)

        self.btnHome = QPushButton("Home ($H)", wgt); self.btnHome.setFixedHeight(28)
        self.btnHome.clicked.connect(lambda: self.sendCommand("$H"))
        self.btnUnlock = QPushButton("Unlock ($X)", wgt); self.btnUnlock.setFixedHeight(28)
        self.btnUnlock.clicked.connect(lambda: self.sendCommand("$X"))
        self.btnSleep = QPushButton("Sleep ($SLP)", wgt); self.btnSleep.setFixedHeight(28)
        self.btnSleep.clicked.connect(lambda: self.sendCommand("$SLP"))
        self.btnDoor = QPushButton("Door", wgt); self.btnDoor.setFixedHeight(28)
        self.btnDoor.clicked.connect(lambda: self.sendCommand("\x84"))

        btn_grid.addWidget(self.btnHome, 0, 0)
        btn_grid.addWidget(self.btnUnlock, 0, 1)
        btn_grid.addWidget(self.btnSleep, 1, 0)
        btn_grid.addWidget(self.btnDoor, 1, 1)
        layout.addWidget(grp_actions)

        # Spindle Box
        self.sliSpindle = SliderBox(wgt)
        self.sliSpindle.setTitle("Spindle (RPM)")
        self.sliSpindle.setMaximum(10000)
        self.sliSpindle.setMinimum(0)
        self.sliSpindle.setRatio(100)
        self.sliSpindle.valueChanged.connect(self._on_spindle_speed_changed)
        self.sliSpindle.toggled.connect(self._on_spindle_toggled)
        layout.addWidget(self.sliSpindle)

        # Jogging Controls
        grp_jog = QGroupBox("Jogging", wgt)
        jog_layout = QVBoxLayout(grp_jog)
        jog_layout.setContentsMargins(6, 6, 6, 6)
        jog_layout.setSpacing(6)

        row_params = QHBoxLayout()
        row_params.addWidget(QLabel("Step:"))
        self.cboJogStep = QComboBox(wgt)
        self.cboJogStep.addItems(["0.01", "0.1", "1", "5", "10", "100"])
        self.cboJogStep.setCurrentIndex(3)
        row_params.addWidget(self.cboJogStep)

        row_params.addWidget(QLabel("Feed:"))
        self.cboJogFeed = QComboBox(wgt)
        self.cboJogFeed.addItems(["10", "50", "100", "500", "1000", "2000"])
        self.cboJogFeed.setCurrentIndex(4)
        row_params.addWidget(self.cboJogFeed)
        jog_layout.addLayout(row_params)

        jog_grid_widget = QWidget(wgt)
        jog_grid = QGridLayout(jog_grid_widget)
        jog_grid.setContentsMargins(0, 0, 0, 0)
        jog_grid.setSpacing(4)

        self.btnJogYPlus = QPushButton("Y+ ▲", wgt)
        self.btnJogYMinus = QPushButton("Y- ▼", wgt)
        self.btnJogXMinus = QPushButton("◀ X-", wgt)
        self.btnJogXPlus = QPushButton("X+ ▶", wgt)
        self.btnJogZPlus = QPushButton("Z+ ▲", wgt)
        self.btnJogZMinus = QPushButton("Z- ▼", wgt)

        for btn in (self.btnJogYPlus, self.btnJogYMinus, self.btnJogXMinus,
                    self.btnJogXPlus, self.btnJogZPlus, self.btnJogZMinus):
            btn.setFixedSize(54, 34)
            btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        self.btnJogYPlus.clicked.connect(lambda: self.jogAxis("Y", 1))
        self.btnJogYMinus.clicked.connect(lambda: self.jogAxis("Y", -1))
        self.btnJogXMinus.clicked.connect(lambda: self.jogAxis("X", -1))
        self.btnJogXPlus.clicked.connect(lambda: self.jogAxis("X", 1))
        self.btnJogZPlus.clicked.connect(lambda: self.jogAxis("Z", 1))
        self.btnJogZMinus.clicked.connect(lambda: self.jogAxis("Z", -1))

        jog_grid.addWidget(self.btnJogYPlus, 0, 1)
        jog_grid.addWidget(self.btnJogXMinus, 1, 0)
        jog_grid.addWidget(self.btnJogXPlus, 1, 2)
        jog_grid.addWidget(self.btnJogYMinus, 2, 1)
        jog_grid.addWidget(self.btnJogZPlus, 0, 3)
        jog_grid.addWidget(self.btnJogZMinus, 2, 3)

        jog_layout.addWidget(jog_grid_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        self.chkJogKeyboard = QCheckBox("Keyboard Control (Arrows/PgUp/PgDn)", wgt)
        jog_layout.addWidget(self.chkJogKeyboard)

        layout.addWidget(grp_jog)

        # Real-time Overrides
        grp_overrides = QGroupBox("Overrides", wgt)
        ov_layout = QVBoxLayout(grp_overrides)
        ov_layout.setContentsMargins(6, 6, 6, 6)
        ov_layout.setSpacing(4)

        self.sliFeedOverride = SliderBox(wgt)
        self.sliFeedOverride.setTitle("Feed Rate %")
        self.sliFeedOverride.setMinimum(10)
        self.sliFeedOverride.setMaximum(200)
        self.sliFeedOverride.setValue(100)
        self.sliFeedOverride.setCheckable(False)
        self.sliFeedOverride.valueChanged.connect(self._on_feed_override_changed)
        ov_layout.addWidget(self.sliFeedOverride)

        self.sliRapidOverride = SliderBox(wgt)
        self.sliRapidOverride.setTitle("Rapid Rate %")
        self.sliRapidOverride.setMinimum(25)
        self.sliRapidOverride.setMaximum(100)
        self.sliRapidOverride.setValue(100)
        self.sliRapidOverride.setCheckable(False)
        self.sliRapidOverride.valueChanged.connect(self._on_rapid_override_changed)
        ov_layout.addWidget(self.sliRapidOverride)

        self.sliSpindleOverride = SliderBox(wgt)
        self.sliSpindleOverride.setTitle("Spindle Speed %")
        self.sliSpindleOverride.setMinimum(50)
        self.sliSpindleOverride.setMaximum(150)
        self.sliSpindleOverride.setValue(100)
        self.sliSpindleOverride.setCheckable(False)
        self.sliSpindleOverride.valueChanged.connect(self._on_spindle_override_changed)
        ov_layout.addWidget(self.sliSpindleOverride)

        layout.addWidget(grp_overrides)
        layout.addStretch(1)

        scroll.setWidget(wgt)
        self.dockDevice.setWidget(scroll)

    def _build_heightmap_dock(self):
        self.dockModification = QDockWidget("Heightmap / Auto-Leveling", self)
        self.dockModification.setObjectName("dockModification")
        self.dockModification.setMinimumWidth(280)

        scroll = QScrollArea(self.dockModification)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        wgt = QWidget(scroll)
        layout = QVBoxLayout(wgt)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # File IO buttons
        row_file = QHBoxLayout()
        self.btnHmCreate = QPushButton("Create", wgt); self.btnHmCreate.setFixedHeight(28)
        self.btnHmCreate.clicked.connect(self._on_hm_create)
        self.btnHmOpen = QPushButton("Open...", wgt); self.btnHmOpen.setFixedHeight(28)
        self.btnHmOpen.clicked.connect(self._on_hm_open)
        self.btnHmSave = QPushButton("Save...", wgt); self.btnHmSave.setFixedHeight(28)
        self.btnHmSave.clicked.connect(self._on_hm_save)
        row_file.addWidget(self.btnHmCreate)
        row_file.addWidget(self.btnHmOpen)
        row_file.addWidget(self.btnHmSave)
        layout.addLayout(row_file)

        # Border Bounds
        grp_border = QGroupBox("Border", wgt)
        grid_b = QGridLayout(grp_border)
        grid_b.setContentsMargins(6, 6, 6, 6)
        grid_b.setSpacing(4)

        self.spnHmX = QDoubleSpinBox(wgt); self.spnHmX.setRange(-5000, 5000)
        self.spnHmY = QDoubleSpinBox(wgt); self.spnHmY.setRange(-5000, 5000)
        self.spnHmW = QDoubleSpinBox(wgt); self.spnHmW.setRange(1, 5000); self.spnHmW.setValue(100)
        self.spnHmH = QDoubleSpinBox(wgt); self.spnHmH.setRange(1, 5000); self.spnHmH.setValue(100)

        grid_b.addWidget(QLabel("X:"), 0, 0); grid_b.addWidget(self.spnHmX, 0, 1)
        grid_b.addWidget(QLabel("Y:"), 0, 2); grid_b.addWidget(self.spnHmY, 0, 3)
        grid_b.addWidget(QLabel("W:"), 1, 0); grid_b.addWidget(self.spnHmW, 1, 1)
        grid_b.addWidget(QLabel("H:"), 1, 2); grid_b.addWidget(self.spnHmH, 1, 3)

        self.btnHmAutoBorder = QPushButton("Auto (From G-Code)", wgt)
        self.btnHmAutoBorder.setFixedHeight(26)
        self.btnHmAutoBorder.clicked.connect(self._on_hm_auto_border)
        grid_b.addWidget(self.btnHmAutoBorder, 2, 0, 1, 4)

        layout.addWidget(grp_border)

        # Grid settings
        grp_grid = QGroupBox("Probe Grid", wgt)
        grid_g = QGridLayout(grp_grid)
        grid_g.setContentsMargins(6, 6, 6, 6)
        grid_g.setSpacing(4)

        self.spnHmGridX = QSpinBox(wgt); self.spnHmGridX.setRange(2, 50); self.spnHmGridX.setValue(5)
        self.spnHmGridY = QSpinBox(wgt); self.spnHmGridY.setRange(2, 50); self.spnHmGridY.setValue(5)

        self.spnHmZTop = QDoubleSpinBox(wgt); self.spnHmZTop.setRange(-100, 100); self.spnHmZTop.setValue(2.0)
        self.spnHmZBottom = QDoubleSpinBox(wgt); self.spnHmZBottom.setRange(-100, 100); self.spnHmZBottom.setValue(-2.0)

        self.spnHmFeed = QDoubleSpinBox(wgt); self.spnHmFeed.setRange(1, 1000); self.spnHmFeed.setValue(20.0)

        grid_g.addWidget(QLabel("Grid X:"), 0, 0); grid_g.addWidget(self.spnHmGridX, 0, 1)
        grid_g.addWidget(QLabel("Grid Y:"), 0, 2); grid_g.addWidget(self.spnHmGridY, 0, 3)
        grid_g.addWidget(QLabel("Z Top:"), 1, 0); grid_g.addWidget(self.spnHmZTop, 1, 1)
        grid_g.addWidget(QLabel("Z Bottom:"), 1, 2); grid_g.addWidget(self.spnHmZBottom, 1, 3)
        grid_g.addWidget(QLabel("Feed:"), 2, 0); grid_g.addWidget(self.spnHmFeed, 2, 1)

        self.btnHmProbe = QPushButton("Probe Workpiece", wgt)
        self.btnHmProbe.setFixedHeight(30)
        self.btnHmProbe.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold;")
        self.btnHmProbe.clicked.connect(self.startProbing)
        grid_g.addWidget(self.btnHmProbe, 3, 0, 1, 4)

        layout.addWidget(grp_grid)

        # Heightmap Table
        self.tblHeightMap = QTableView(wgt)
        self.tblHeightMap.setModel(self.m_heightMapModel)
        self.tblHeightMap.setFixedHeight(150)
        self.tblHeightMap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.tblHeightMap.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.m_heightMapModel.dataChangedByUserInput.connect(self._on_hm_table_edited)
        layout.addWidget(self.tblHeightMap)

        # Options
        self.chkHmShowBorder = QCheckBox("Show Border", wgt)
        self.chkHmShowBorder.setChecked(True)
        self.chkHmShowBorder.toggled.connect(lambda v: self.m_heightMapBorderDrawer.setVisible(v))

        self.chkHmShowGrid = QCheckBox("Show Grid & Points", wgt)
        self.chkHmShowGrid.setChecked(True)
        self.chkHmShowGrid.toggled.connect(lambda v: self.m_heightMapGridDrawer.setVisible(v))

        self.chkHmShowInterpolation = QCheckBox("Show Elevation Mesh", wgt)
        self.chkHmShowInterpolation.setChecked(True)
        self.chkHmShowInterpolation.toggled.connect(lambda v: self.m_heightMapInterpolationDrawer.setVisible(v))

        self.chkHmUse = QCheckBox("Use Heightmap (Z-Deformation)", wgt)
        self.chkHmUse.setStyleSheet("font-weight: bold; color: #4caf50;")
        self.chkHmUse.toggled.connect(self._on_hm_use_toggled)

        layout.addWidget(self.chkHmShowBorder)
        layout.addWidget(self.chkHmShowGrid)
        layout.addWidget(self.chkHmShowInterpolation)
        layout.addWidget(self.chkHmUse)
        layout.addStretch(1)

        scroll.setWidget(wgt)
        self.dockModification.setWidget(scroll)

    def _build_console_dock(self):
        self.dockConsole = QDockWidget("Console", self)
        self.dockConsole.setObjectName("dockConsole")
        wgt = QWidget(self.dockConsole)
        layout = QVBoxLayout(wgt)
        layout.setContentsMargins(4, 4, 4, 4)

        self.txtConsole = QTextEdit(wgt)
        self.txtConsole.setReadOnly(True)
        self.txtConsole.setFont(QFont("Consolas", 9))
        layout.addWidget(self.txtConsole)

        input_row = QHBoxLayout()
        self.cboCommand = ComboBoxKey(wgt)
        self.cboCommand.setPlaceholderText("Enter G-code command (e.g. G0 X0 Y0 or $$)")
        self.cboCommand.lineEdit().returnPressed.connect(self._on_console_send)

        self.btnConsoleSend = QPushButton("Send", wgt)
        self.btnConsoleSend.clicked.connect(self._on_console_send)

        self.btnConsoleClear = QPushButton("Clear", wgt)
        self.btnConsoleClear.clicked.connect(self.txtConsole.clear)

        input_row.addWidget(self.cboCommand)
        input_row.addWidget(self.btnConsoleSend)
        input_row.addWidget(self.btnConsoleClear)
        layout.addLayout(input_row)

        self.dockConsole.setWidget(wgt)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockConsole)

    def _build_user_dock(self):
        self.dockUser = QDockWidget("Custom Macros & Command Chains", self)
        self.dockUser.setObjectName("dockUser")
        
        wgt = QWidget(self.dockUser)
        main_layout = QVBoxLayout(wgt)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Header with Open Macro Builder
        hdr = QHBoxLayout()
        lbl_info = QLabel("<b>Custom Macro Buttons:</b>", wgt)
        self.btnOpenMacroBuilder = QPushButton("🛠 Macro Builder / Editor...", wgt)
        self.btnOpenMacroBuilder.setStyleSheet("font-weight: bold; background: #1976d2; color: white;")
        self.btnOpenMacroBuilder.clicked.connect(self.openMacroBuilder)
        hdr.addWidget(lbl_info)
        hdr.addStretch()
        hdr.addWidget(self.btnOpenMacroBuilder)
        main_layout.addLayout(hdr)

        # Scroll area for dynamic macro buttons
        scroll = QScrollArea(wgt)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.wgtMacroButtons = QWidget()
        self.gridMacroButtons = QGridLayout(self.wgtMacroButtons)
        self.gridMacroButtons.setContentsMargins(2, 2, 2, 2)
        self.gridMacroButtons.setSpacing(6)
        scroll.setWidget(self.wgtMacroButtons)
        main_layout.addWidget(scroll, stretch=1)

        self.dockUser.setWidget(wgt)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockUser)
        self._rebuild_macro_buttons()

    def _rebuild_macro_buttons(self):
        while self.gridMacroButtons.count():
            item = self.gridMacroButtons.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        macros = self.m_macroManager.macros()
        cols = 3
        for i, macro in enumerate(macros):
            r, c = divmod(i, cols)
            btn = QPushButton(macro.name, self.wgtMacroButtons)
            btn.setMinimumHeight(34)
            color = macro.color or "#1976d2"
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {color}; color: white; font-weight: bold; "
                f"border-radius: 4px; padding: 4px 8px; font-size: 11px; }} "
                f"QPushButton:hover {{ background-color: #333333; border: 1px solid {color}; }} "
                f"QPushButton:pressed {{ background-color: #111111; }}"
            )
            btn.setToolTip(f"Execute Macro Chain '{macro.name}' ({len(macro.blocks)} steps)")
            btn.clicked.connect(lambda ch, m=macro: self.m_macroRunner.runMacro(m))
            self.gridMacroButtons.addWidget(btn, r, c)

    def openMacroBuilder(self):
        dlg = MacroBuilderDialog(self.m_macroManager, self.m_macroRunner, self)
        dlg.exec()
        self._rebuild_macro_buttons()

    def _build_script_dock(self):
        self.dockScript = QDockWidget("Scripting", self)
        self.dockScript.setObjectName("dockScript")
        self.scriptWidget = ScriptWidget(self, self.dockScript)
        self.dockScript.setWidget(self.scriptWidget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockScript)
        self.dockScript.hide()

    def _build_log_dock(self):
        self.dockLog = QDockWidget("Log", self)
        self.dockLog.setObjectName("dockLog")
        self.logWidget = LogWidget(self.dockLog)
        self.dockLog.setWidget(self.logWidget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockLog)
        self.dockLog.hide()

    def _build_menus(self):
        mb = self.menuBar()

        # File Menu
        m_file = mb.addMenu("&File")
        act_open = m_file.addAction("&Open G-Code...")
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self.openFile)

        act_new = m_file.addAction("&New / Clear")
        act_new.triggered.connect(self.newFile)

        act_save = m_file.addAction("&Save G-Code...")
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self.saveFile)

        m_file.addSeparator()
        act_exit = m_file.addAction("E&xit")
        act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        act_exit.triggered.connect(self.close)

        # Edit Menu
        m_edit = mb.addMenu("&Edit")
        act_undo = m_edit.addAction("&Undo")
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        act_undo.triggered.connect(self.m_programTableHistory.undo)

        act_redo = m_edit.addAction("&Redo")
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        act_redo.triggered.connect(self.m_programTableHistory.redo)

        # View Menu
        m_view = mb.addMenu("&View")
        act_fit = m_view.addAction("&Fit Visualizer")
        act_fit.triggered.connect(lambda: self.glwVisualizer.fitDrawable(self.m_codeDrawer))

        m_view.addSeparator()
        m_view.addAction(self.dockVisualizer.toggleViewAction())
        m_view.addAction(self.dockDevice.toggleViewAction())
        m_view.addAction(self.dockModification.toggleViewAction())
        m_view.addAction(self.dockConsole.toggleViewAction())
        m_view.addAction(self.dockUser.toggleViewAction())
        m_view.addAction(self.dockScript.toggleViewAction())
        m_view.addAction(self.dockLog.toggleViewAction())

        # Service Menu
        m_service = mb.addMenu("&Service")
        act_macro_builder = m_service.addAction("&Macro Builder / Editor...")
        act_macro_builder.triggered.connect(self.openMacroBuilder)
        
        act_settings = m_service.addAction("&Settings...")
        act_settings.setShortcut(QKeySequence.StandardKey.Preferences)
        act_settings.triggered.connect(self.openSettings)

        # Help Menu
        m_help = mb.addMenu("&Help")
        act_doc = m_help.addAction("&Documentation...")
        act_doc.triggered.connect(lambda: HelpDialog(self).exec())

        act_check = m_help.addAction("&Safety Checklist...")
        act_check.triggered.connect(lambda: ChecklistDialog(self).exec())

        act_about = m_help.addAction("&About Candle...")
        act_about.triggered.connect(lambda: AboutDialog(self).exec())

    def _toggle_connection(self):
        if self.m_connection and self.m_connection.isConnected():
            self.m_connection.close()
        else:
            self._setup_connection()

    def _setup_connection(self):
        if self.m_connection:
            try:
                self.m_connection.close()
            except Exception:
                pass
            self.m_connection = None

        conn_type = self.m_storage.get("Connection/type", int(ConnectionType.Serial))

        if conn_type == int(ConnectionType.Serial):
            port = self.m_storage.get("Connection/port", "")
            baud = int(self.m_storage.get("Connection/baud", 115200))
            if port:
                if hasattr(self, 'lblConnInfo'):
                    self.lblConnInfo.setText(f"{port} @ {baud}")
                self.logWidget.appendLog(f"Opening serial port {port} at {baud} baud...", "INFO")
                self.txtConsole.append(f"Opening serial port {port} at {baud} baud...")
                self.m_connection = SerialPortConnection(port, baud, self)
            else:
                if hasattr(self, 'lblConnInfo'):
                    self.lblConnInfo.setText("No Port Configured")
                self.logWidget.appendLog("No serial port configured. Please select port in Service -> Settings.", "WARN")
                self.lblState.setText("NO PORT")
                self.lblState.setStyleSheet(
                    "font-weight: bold; font-size: 13px; background-color: #f57c00; color: white; "
                    "border-radius: 4px; padding: 4px;"
                )
                return
        elif conn_type == int(ConnectionType.Telnet):
            addr = self.m_storage.get("Connection/telnetAddress", "192.168.1.100")
            port = int(self.m_storage.get("Connection/telnetPort", 23))
            if hasattr(self, 'lblConnInfo'):
                self.lblConnInfo.setText(f"Telnet: {addr}:{port}")
            self.logWidget.appendLog(f"Connecting to Telnet {addr}:{port}...", "INFO")
            self.txtConsole.append(f"Connecting to Telnet {addr}:{port}...")
            self.m_connection = TelnetConnection(addr, port, self)
        elif conn_type == int(ConnectionType.WebSocket):
            url = self.m_storage.get("Connection/webSocketUrl", "ws://192.168.1.100:81")
            binary = bool(self.m_storage.get("Connection/webSocketBinary", False))
            if hasattr(self, 'lblConnInfo'):
                self.lblConnInfo.setText(f"WS: {url}")
            self.logWidget.appendLog(f"Connecting to WebSocket {url}...", "INFO")
            self.txtConsole.append(f"Connecting to WebSocket {url}...")
            self.m_connection = WebSocketConnection(url, binary, self)

        if self.m_connection:
            self.m_connection.connected.connect(self._on_connected)
            self.m_connection.disconnected.connect(self._on_disconnected)
            self.m_connection.dataReceived.connect(self._on_data_received)
            self.m_connection.errorOccurred.connect(self._on_connection_error)
            self.m_connection.open()

    def _apply_settings(self):
        s = self.m_storage
        # Visualizer colors & rendering
        c_bg = QColor(str(s.get("Visualizer/colorBackground", "#1e1e1e")))
        c_txt = QColor(str(s.get("Visualizer/colorText", "#ffffff")))
        c_norm = QColor(str(s.get("Visualizer/colorNormal", "#4d90fe")))
        c_high = QColor(str(s.get("Visualizer/colorHighlight", "#ffff00")))
        c_z = QColor(str(s.get("Visualizer/colorZMovement", "#ff3333")))
        c_drawn = QColor(str(s.get("Visualizer/colorDrawn", "#888888")))

        self.glwVisualizer.setColors(c_bg, c_txt)
        self.m_codeDrawer.setColorNormal(c_norm)
        self.m_codeDrawer.setColorHighlight(c_high)
        self.m_codeDrawer.setColorZMovement(c_z)
        self.m_codeDrawer.setColorDrawn(c_drawn)

        # Machine bounds
        bx = float(s.get("Control/machineBoundsX", 300.0))
        by = float(s.get("Control/machineBoundsY", 180.0))
        bz = float(s.get("Control/machineBoundsZ", 45.0))
        self.m_boundsDrawer.setDimensions(bx, by, bz)

        # Query timer
        q_time = int(s.get("Control/queryStateTime", 200))
        self.m_statusQueryTimer.setInterval(q_time)

    def _on_connected(self):
        port = self.m_storage.get("Connection/port", "")
        self.lblState.setText("CONNECTED")
        self.lblState.setStyleSheet("font-weight: bold; font-size: 13px; background-color: #2e7d32; color: white; border-radius: 4px; padding: 4px;")
        if hasattr(self, 'btnConnectToggle'):
            self.btnConnectToggle.setText("Disconnect")
        if hasattr(self, 'lblConnInfo'):
            self.lblConnInfo.setText(f"Connected: {port}")
        self.logWidget.appendLog(f"Connected to controller on {port}.", "INFO")
        self.txtConsole.append(f"Connected to controller on {port}.")
        self.m_statusQueryTimer.start()

        if self.m_storage.get("Connection/resetOnConnection", True):
            QTimer.singleShot(300, lambda: self.sendCommand("\x18"))

    def _on_disconnected(self):
        self.lblState.setText("DISCONNECTED")
        self.lblState.setStyleSheet("font-weight: bold; font-size: 13px; background-color: #c62828; color: white; border-radius: 4px; padding: 4px;")
        if hasattr(self, 'btnConnectToggle'):
            self.btnConnectToggle.setText("Connect")
        if hasattr(self, 'lblConnInfo'):
            self.lblConnInfo.setText("Not connected")
        self.logWidget.appendLog("Disconnected from controller.", "WARN")
        self.txtConsole.append("Disconnected from controller.")
        self.m_statusQueryTimer.stop()

    def _on_connection_error(self, err: str):
        self.lblState.setText("PORT ERROR")
        self.lblState.setStyleSheet("font-weight: bold; font-size: 13px; background-color: #d32f2f; color: white; border-radius: 4px; padding: 4px;")
        if hasattr(self, 'btnConnectToggle'):
            self.btnConnectToggle.setText("Connect")
        self.logWidget.appendLog(f"Connection Error: {err}", "ERROR")
        self.txtConsole.append(f"[CONNECTION ERROR] {err}")

    def _query_status(self):
        if self.m_connection and self.m_connection.isConnected():
            self.m_connection.send("?")

    def sendCommand(self, cmd: str):
        if self.m_connection and self.m_connection.isConnected():
            self.m_connection.send(cmd)

    def sendConsoleCommand(self, cmd: str):
        self.txtConsole.append(f"> {cmd}")
        self.sendCommand(cmd)

    def _on_console_send(self):
        cmd = self.cboCommand.currentText().strip()
        if not cmd:
            return
        if self.cboCommand.findText(cmd) == -1:
            self.cboCommand.addItem(cmd)
        self.sendConsoleCommand(cmd)
        self.cboCommand.setEditText("")

    def _on_data_received(self, line: str):
        # Check if line is a status report <Idle|MPos:...>
        if line.startswith("<") and line.endswith(">"):
            self._parse_status_report(line)
            return

        # Check if line is a probe result [PRB:0.000,0.000,-1.234:1]
        if line.startswith("[PRB:") and line.endswith("]"):
            self._parse_probe_report(line)
            return

        # Check if line is an alarm message
        if line.startswith("ALARM:") or line.startswith("alarm:") or "Hard limit" in line or "Soft limit" in line:
            self.txtConsole.append(f"<span style='color:#ff5555; font-weight:bold;'>{line}</span>")
            self.logWidget.appendLog(f"Controller: {line}", "WARN")
            if self.m_senderState == SenderState.Transferring:
                self.abortStreaming()
                self.sendCommand("M5")  # Stop spindle on real file execution alarm
            else:
                self._recover_from_jog_limit()
            return

        # Normal console / response output
        self.txtConsole.append(line)

        # Streaming buffer management for ok / error
        if line.startswith("ok") or line.startswith("error:"):
            if self.m_bufferLength:
                self.m_bufferLength.pop(0)
            self._feed_stream_queue()

    def _parse_status_report(self, report: str):
        content = report[1:-1]
        tokens = content.split("|")
        if not tokens:
            return

        state_str = tokens[0]
        # Match device state
        for prefix, st in DEVICE_STATUS_STRINGS.items():
            if state_str.startswith(prefix):
                self.m_deviceState = st
                break

        # Check for Alarm state handling
        if self.m_deviceState == DeviceState.Alarm:
            if self.m_senderState == SenderState.Transferring:
                self.abortStreaming()
                self.sendCommand("M5")
            elif not getattr(self, 'm_isRecoveringFromLimit', False):
                self._recover_from_jog_limit()

        # Update status box UI
        caption = STATUS_CAPTIONS.get(self.m_deviceState, state_str)
        back = STATUS_BACK_COLORS.get(self.m_deviceState, "palette(button)")
        fore = STATUS_FORE_COLORS.get(self.m_deviceState, "palette(text)")
        self.lblState.setText(caption)
        self.lblState.setStyleSheet(f"font-weight: bold; font-size: 14px; background-color: {back}; color: {fore}; padding: 4px; border-radius: 3px;")
        self.glwVisualizer.setParserStatus(caption)

        # Parse MPos, WPos, WCO, FS, Ov, Pn
        for tok in tokens[1:]:
            if tok.startswith("MPos:"):
                coords = [float(x) for x in tok[5:].split(",")]
                if len(coords) >= 3:
                    self.m_mpos = QVector3D(coords[0], coords[1], coords[2])
                    self.lblMPosX.setText(f"{coords[0]:.3f}")
                    self.lblMPosY.setText(f"{coords[1]:.3f}")
                    self.lblMPosZ.setText(f"{coords[2]:.3f}")
                    if len(coords) >= 4:
                        self.m_axisA_mpos = coords[3]
                        self.lblMPosA.setText(f"{coords[3]:.3f}")
                    # Update WPos = MPos - WCO
                    self.m_wpos = self.m_mpos - self.m_wco
                    self.lblWPosX.setText(f"{self.m_wpos.x():.3f}")
                    self.lblWPosY.setText(f"{self.m_wpos.y():.3f}")
                    self.lblWPosZ.setText(f"{self.m_wpos.z():.3f}")
                    self.m_toolDrawer.setToolPosition(self.m_wpos)
                    self.glwVisualizer.setCursorPos(self.m_wpos)
            elif tok.startswith("WPos:"):
                coords = [float(x) for x in tok[5:].split(",")]
                if len(coords) >= 3:
                    self.m_wpos = QVector3D(coords[0], coords[1], coords[2])
                    self.lblWPosX.setText(f"{coords[0]:.3f}")
                    self.lblWPosY.setText(f"{coords[1]:.3f}")
                    self.lblWPosZ.setText(f"{coords[2]:.3f}")
                    self.m_toolDrawer.setToolPosition(self.m_wpos)
                    self.glwVisualizer.setCursorPos(self.m_wpos)
            elif tok.startswith("WCO:"):
                coords = [float(x) for x in tok[4:].split(",")]
                if len(coords) >= 3:
                    self.m_wco = QVector3D(coords[0], coords[1], coords[2])
            elif tok.startswith("FS:"):
                self.glwVisualizer.setSpeedState(tok)
            elif tok.startswith("Pn:"):
                self.glwVisualizer.setPinState(tok)

        # Buffer status in HUD
        buf_used = sum(self.m_bufferLength)
        self.glwVisualizer.setBufferState(f"Buffer: {buf_used}/{BUFFER_LENGTH} ({int(buf_used*100/BUFFER_LENGTH)}%)")

    def _parse_probe_report(self, report: str):
        # Format: [PRB:X,Y,Z:1]
        m = re.search(r'\[PRB:([-\d.]+),([-\d.]+),([-\d.]+):(\d+)\]', report)
        if m:
            px = float(m.group(1))
            py = float(m.group(2))
            pz = float(m.group(3))
            succ = (int(m.group(4)) == 1)

            # 1. Route to Macro Runner if active
            if hasattr(self, 'm_macroRunner') and self.m_macroRunner.isRunning():
                self.m_macroRunner.onProbeReportReceived(pz, succ)
                return

            # 2. Touch Plate Zeroing Routine
            if getattr(self, 'm_isZeroProbing', False):
                self._handle_zero_probe_result(pz, succ)
                return

            # 3. Heightmap auto-level probing
            if succ and self.m_isProbing:
                self._record_probe_point(pz)

    def _record_probe_point(self, z_val: float):
        cols = self.m_heightMapModel.columnCount()
        rows = self.m_heightMapModel.rowCount()
        if self.m_probeIndex < cols * rows:
            r = self.m_probeIndex // cols
            c = self.m_probeIndex % cols
            # Snake pattern: alternate columns on odd rows
            actual_col = (cols - 1 - c) if (r % 2 == 1) else c
            idx = self.m_heightMapModel.index(r, actual_col)
            self.m_heightMapModel.setData(idx, z_val, Qt.ItemDataRole.UserRole)
            self.m_probeIndex += 1
            self._update_heightmap_drawers()

    def _update_heightmap_drawers(self):
        rect = QRectF(
            self.spnHmX.value(), self.spnHmY.value(),
            self.spnHmW.value(), self.spnHmH.value()
        )
        self.m_heightMapBorderDrawer.setBorderRect(rect)
        self.m_heightMapGridDrawer.setBorderRect(rect)
        self.m_heightMapGridDrawer.setZLimits(self.spnHmZTop.value(), self.spnHmZBottom.value())
        self.m_heightMapGridDrawer.update()

        mesh = HeightMapManager.generateInterpolationMesh(
            rect, self.m_heightMapModel, 2.0, 2.0
        )
        self.m_heightMapInterpolationDrawer.setBorderRect(rect)
        self.m_heightMapInterpolationDrawer.setData(mesh)
        self.glwVisualizer.update()

    # Streaming Engine
    def startStreaming(self):
        if self.m_senderState == SenderState.Paused:
            self.m_senderState = SenderState.Transferring
            self.sendCommand("~")
            return

        if self.m_programModel.rowCount() == 0:
            return

        self.m_queue.clear()

        # Safe Travel: Lift Z to near top limit in machine coordinates before moving
        if self.chkSafeTravel.isChecked():
            clearance = float(self.m_storage.get("Control/safeTravelClearance", 3.0))
            self.m_queue.append(f"G53 G0 Z-{clearance:.3f}")
            self.logWidget.appendLog(f"Safe Travel: Retracting spindle to top clearance (G53 Z-{clearance:.3f}) before starting.", "INFO")
            self.txtConsole.append(f"<span style='color:#4caf50;'>[SAFE TRAVEL] Retracting to G53 Z-{clearance:.3f} before job start.</span>")

        for item in self.m_programModel.items():
            cmd = item.command.strip()
            if cmd:
                self.m_queue.append(cmd)

        # Safe Travel: Retract Z to near top limit and stop spindle after finishing
        if self.chkSafeTravel.isChecked():
            clearance = float(self.m_storage.get("Control/safeTravelClearance", 3.0))
            self.m_queue.append("M5")  # Stop spindle
            self.m_queue.append(f"G53 G0 Z-{clearance:.3f}")  # Retract Z
            self.logWidget.appendLog(f"Safe Travel: Queued post-job spindle stop and retract to G53 Z-{clearance:.3f}.", "INFO")

        self.m_queueCommandIndex = 0
        self.m_bufferLength.clear()
        self.m_senderState = SenderState.Transferring
        self.m_startTime = time.time()
        self.m_elapsedTimer.start(1000)

        self._feed_stream_queue()

    def _feed_stream_queue(self):
        if self.m_senderState != SenderState.Transferring:
            return

        while self.m_queueCommandIndex < len(self.m_queue):
            cmd = self.m_queue[self.m_queueCommandIndex]
            cmd_len = len(cmd) + 1

            if sum(self.m_bufferLength) + cmd_len <= BUFFER_LENGTH:
                self.m_bufferLength.append(cmd_len)
                self.sendCommand(cmd)

                if self.m_queueCommandIndex < self.m_programModel.rowCount():
                    self.m_programModel.setData(
                        self.m_programModel.index(self.m_queueCommandIndex, 2),
                        int(GCodeItemState.Sent),
                        Qt.ItemDataRole.EditRole
                    )

                # Update progress slider & auto-scroll
                self.sliProgram.setValue(min(self.m_queueCommandIndex, self.sliProgram.maximum()))
                self.lblProgramProgress.setText(f"{self.m_queueCommandIndex + 1} / {len(self.m_queue)}")
                if self.chkAutoScroll.isChecked() and self.m_queueCommandIndex < self.m_programModel.rowCount():
                    self.tblProgram.scrollTo(self.m_programModel.index(self.m_queueCommandIndex, 0))

                self.m_queueCommandIndex += 1
            else:
                break

        if self.m_queueCommandIndex >= len(self.m_queue) and not self.m_bufferLength:
            self.m_senderState = SenderState.Stopped
            self.m_elapsedTimer.stop()
            self.logWidget.appendLog("Job Completed Successfully.", "INFO")
            self.txtConsole.append("<span style='color:#4caf50; font-weight:bold;'>[JOB COMPLETE] Finished G-code program safely.</span>")

    def pauseStreaming(self):
        if self.m_senderState == SenderState.Transferring:
            self.m_senderState = SenderState.Paused
            self.sendCommand("!")
        elif self.m_senderState == SenderState.Paused:
            self.m_senderState = SenderState.Transferring
            self.sendCommand("~")

    def abortStreaming(self):
        self.m_senderState = SenderState.Stopped
        self.m_queue.clear()
        self.m_bufferLength.clear()
        self.m_elapsedTimer.stop()
        self.sendCommand("!")
        self.sendCommand("\x18")  # Reset

    def resetDevice(self):
        self.sendCommand("\x18")

    def checkMode(self):
        self.sendCommand("$C")

    def _update_elapsed_time(self):
        secs = int(time.time() - self.m_startTime)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        t_elapsed = QTime(h, m, s)
        self.glwVisualizer.setTimes(t_elapsed, QTime(0, 0, 0))

    # Jogging
    def jogAxis(self, axis: str, direction: int):
        self.m_lastJogAxis = axis
        self.m_lastJogDirection = direction
        self.m_lastJogTime = time.time()
        step = float(self.cboJogStep.currentText()) * direction
        feed = float(self.cboJogFeed.currentText())
        cmd = f"$J=G91 {axis}{step:.3f} F{feed:.0f}"
        self.sendCommand(cmd)

    def _recover_from_jog_limit(self):
        if getattr(self, 'm_isRecoveringFromLimit', False):
            return
        self.m_isRecoveringFromLimit = True

        axis = getattr(self, 'm_lastJogAxis', 'Z')
        direction = getattr(self, 'm_lastJogDirection', 1)
        pull_off = -2.0 * direction  # 2mm bounce-back in opposite direction

        self.lblState.setText("LIMIT BOUNCE")
        self.lblState.setStyleSheet(
            "font-weight: bold; font-size: 13px; background-color: #ff9800; color: white; "
            "border-radius: 4px; padding: 4px;"
        )
        self.logWidget.appendLog(f"Limit switch hit on {axis}. Auto-unlocking and backing off {abs(pull_off):.1f}mm...", "WARN")
        self.txtConsole.append(
            f"<span style='color:#ffaa00; font-weight:bold;'>[LIMIT HIT] {axis} limit switch triggered. Auto-unlocking and bouncing back...</span>"
        )

        # Step 1: Soft reset to clear GRBL hard limit halt
        self.sendCommand("\x18")

        # Step 2: Unlock ($X) after 150ms
        QTimer.singleShot(150, lambda: self.sendCommand("$X"))

        # Step 3: Jog away from limit switch after 350ms
        bounce_cmd = f"$J=G91 {axis}{pull_off:.3f} F250"
        QTimer.singleShot(350, lambda: self.sendCommand(bounce_cmd))

        # Step 4: Finish recovery after 800ms
        def _finish_recovery():
            self.m_isRecoveringFromLimit = False
            self.txtConsole.append(
                f"<span style='color:#4caf50; font-weight:bold;'>[RECOVERY READY] Backed off {axis} by {abs(pull_off):.1f}mm. Ready.</span>"
            )
            self._query_status()

        QTimer.singleShot(800, _finish_recovery)

    def zeroAxis(self, axis: str):
        self.sendCommand(f"G92 {axis}0")

    def probeZeroZ(self):
        if self.m_senderState == SenderState.Transferring:
            self.logWidget.appendLog("Cannot probe: G-code streaming is active.", "WARN")
            return
        if not self.m_connection or not self.m_connection.isConnected():
            self.logWidget.appendLog("Cannot probe: Controller is not connected.", "ERROR")
            return

        thickness = float(self.m_storage.get("Control/touchPlateThickness", 15.0))
        dist = float(self.m_storage.get("Control/probeMaxDistance", 30.0))
        feed = float(self.m_storage.get("Control/probeSearchFeed", 40.0))

        self.m_isZeroProbing = True
        self.m_zeroProbeStage = 1

        self.logWidget.appendLog(f"Starting Z-Probe Zeroing (Search: -{dist:.0f}mm at {feed:.0f}mm/min, Plate: {thickness:.2f}mm)...", "INFO")
        self.txtConsole.append(
            f"<span style='color:#2196f3; font-weight:bold;'>[Z-PROBE START] Probing down max {dist:.0f}mm for touch plate ({thickness:.2f}mm)...</span>"
        )

        self.sendCommand("G21 G91")
        self.sendCommand(f"G38.2 Z-{dist:.3f} F{feed:.0f}")

    def _handle_zero_probe_result(self, z_val: float, succ: bool):
        if not succ:
            self.m_isZeroProbing = False
            self.logWidget.appendLog("Z-Probe failed: Touch plate contact not detected within search distance.", "ERROR")
            self.txtConsole.append("<span style='color:red; font-weight:bold;'>[Z-PROBE FAILED] Touch plate contact not detected.</span>")
            return

        if self.m_zeroProbeStage == 1:
            # First search contact made -> lift 1.5mm and perform slow precision latch probe
            self.m_zeroProbeStage = 2
            latch_feed = float(self.m_storage.get("Control/probeLatchFeed", 10.0))
            self.sendCommand("G91 G0 Z1.500")
            self.sendCommand(f"G38.2 Z-3.000 F{latch_feed:.0f}")

        elif self.m_zeroProbeStage == 2:
            # Final precision latch contact made -> set work Z to plate thickness and retract
            self.m_isZeroProbing = False
            thickness = float(self.m_storage.get("Control/touchPlateThickness", 15.0))
            retract = float(self.m_storage.get("Control/probeRetractHeight", 5.0))

            self.sendCommand("G90")
            self.sendCommand(f"G92 Z{thickness:.3f}")
            self.sendCommand(f"G91 G0 Z{retract:.3f}")
            self.sendCommand("G90")

            self.logWidget.appendLog(f"Z-Axis zeroed using touch plate ({thickness:.2f}mm). Retracted {retract:.1f}mm.", "INFO")
            self.txtConsole.append(
                f"<span style='color:#4caf50; font-weight:bold;'>[Z-PROBE SUCCESS] Work Z set to {thickness:.3f}mm (Plate Thickness). Retracted {retract:.1f}mm.</span>"
            )

    def returnAxis(self, axis: str):
        self.sendCommand(f"G90 G0 {axis}0")

    def moveToSafeZ(self):
        safe_z = float(self.m_storage.get("Control/safeZ", 5.0))
        self.sendCommand(f"G90 G0 Z{safe_z:.3f}")

    def sendMacro(self, macro: str):
        for line in macro.strip().split("\n"):
            line = line.strip()
            if line:
                self.sendConsoleCommand(line)

    # Overrides
    def _on_feed_override_changed(self):
        val = self.sliFeedOverride.value()
        # Feed override commands in GRBL
        if val == 100:
            self.sendCommand("\x90")  # 100% reset
        elif val > 100:
            self.sendCommand("\x91")  # +10%
        else:
            self.sendCommand("\x92")  # -10%

    def _on_rapid_override_changed(self):
        val = self.sliRapidOverride.value()
        if val == 100:
            self.sendCommand("\x95")  # 100%
        elif val == 50:
            self.sendCommand("\x96")  # 50%
        elif val == 25:
            self.sendCommand("\x97")  # 25%

    def _on_spindle_override_changed(self):
        val = self.sliSpindleOverride.value()
        if val == 100:
            self.sendCommand("\x99")  # 100%
        elif val > 100:
            self.sendCommand("\x9A")  # +10%
        else:
            self.sendCommand("\x9B")  # -10%

    def _on_spindle_speed_changed(self):
        rpm = self.sliSpindle.value()
        if self.sliSpindle.isChecked():
            self.sendCommand(f"S{rpm}")

    def _on_spindle_toggled(self, checked: bool):
        if checked:
            rpm = self.sliSpindle.value()
            self.sendCommand(f"M3 S{rpm}")
        else:
            self.sendCommand("M5")

    # File IO & G-Code Parsing
    def newFile(self):
        self.m_programModel.clear()
        self.m_parser.reset()
        self.m_viewParser.reset()
        self.m_codeDrawer.update()
        self.m_programFileName = ""
        self.sliProgram.setRange(0, 0)
        self.lblProgramProgress.setText("0 / 0")

    def openFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open G-Code", "", "G-Code Files (*.nc *.ncc *.ngc *.gcode *.tap *.txt);;All Files (*)")
        if not fname:
            return

        self.loadFile(fname)

    def loadFile(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            self.newFile()
            self.m_programFileName = filepath
            commands = [line.strip() for line in lines if line.strip()]

            # Load into table model
            self.m_programModel.insertCommands(0, commands)
            self.sliProgram.setRange(0, max(0, len(commands) - 1))
            self.lblProgramProgress.setText(f"1 / {len(commands)}")

            # Parse G-code
            self.m_parser.reset()
            for cmd in commands:
                self.m_parser.addCommand(cmd)

            self.m_viewParser.reset()
            self.m_viewParser.updateFromParser(self.m_parser)
            self.m_codeDrawer.update()
            self.glwVisualizer.fitDrawable(self.m_codeDrawer)

            # Estimate Job Time
            estimator = TimeEstimator(self.m_viewParser.getLineSegments())
            est_minutes = estimator.calculateTime()
            h = int(est_minutes // 60)
            m = int(est_minutes % 60)
            s = int((est_minutes * 60) % 60)
            self.glwVisualizer.setTimes(QTime(0, 0, 0), QTime(h, m, s))

            self.logWidget.appendLog(f"Loaded '{os.path.basename(filepath)}' ({len(commands)} lines).", "INFO")
        except Exception as e:
            QMessageBox.critical(self, "Error Loading File", str(e))

    def saveFile(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save G-Code", self.m_programFileName or "program.nc", "G-Code Files (*.nc *.gcode);;All Files (*)")
        if not fname:
            return

        try:
            with open(fname, 'w', encoding='utf-8') as f:
                for item in self.m_programModel.items():
                    f.write(item.command + "\n")
            self.logWidget.appendLog(f"Saved '{fname}'.", "INFO")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", str(e))

    def _on_table_row_changed(self, current, previous):
        row = current.row()
        if row >= 0:
            indexes = self.m_viewParser.getLineSegmentIndexes()
            if row < len(indexes):
                seg_idxs = indexes[row]
                if seg_idxs:
                    first_seg = self.m_viewParser.getLineSegments()[seg_idxs[0]]
                    self.m_selectionDrawer.setPosition(first_seg.getStart())
                    self.glwVisualizer.update()

    def _on_slider_moved(self, pos: int):
        self.lblProgramProgress.setText(f"{pos + 1} / {self.m_programModel.rowCount()}")
        self.tblProgram.selectRow(pos)

    # Heightmap routines
    def _on_hm_create(self):
        gx = self.spnHmGridX.value()
        gy = self.spnHmGridY.value()
        self.m_heightMapModel.resize(gx, gy)
        self._update_heightmap_drawers()

    def _on_hm_open(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Heightmap", "", "Candle Map Files (*.map);;All Files (*)")
        if not fname:
            return

        res = HeightMapManager.loadHeightMap(fname)
        if res:
            data, grid = res
            self.spnHmX.setValue(data.borderRect.x())
            self.spnHmY.setValue(data.borderRect.y())
            self.spnHmW.setValue(data.borderRect.width())
            self.spnHmH.setValue(data.borderRect.height())
            self.spnHmGridX.setValue(data.gridX)
            self.spnHmGridY.setValue(data.gridY)
            self.spnHmZTop.setValue(data.zTop)
            self.spnHmZBottom.setValue(data.zBottom)
            self.spnHmFeed.setValue(data.probeFeed)
            self.m_heightMapModel.setRawData(grid)
            self._update_heightmap_drawers()
            self.m_heightMapFileName = fname
            self.logWidget.appendLog(f"Heightmap loaded from '{fname}'.", "INFO")

    def _on_hm_save(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save Heightmap", self.m_heightMapFileName or "heightmap.map", "Candle Map Files (*.map)")
        if not fname:
            return

        data = HeightMapData()
        data.borderRect = QRectF(self.spnHmX.value(), self.spnHmY.value(), self.spnHmW.value(), self.spnHmH.value())
        data.gridX = self.spnHmGridX.value()
        data.gridY = self.spnHmGridY.value()
        data.zTop = self.spnHmZTop.value()
        data.zBottom = self.spnHmZBottom.value()
        data.probeFeed = self.spnHmFeed.value()

        if HeightMapManager.saveHeightMap(fname, data, self.m_heightMapModel):
            self.m_heightMapFileName = fname
            self.logWidget.appendLog(f"Heightmap saved to '{fname}'.", "INFO")

    def _on_hm_auto_border(self):
        bounds_min = self.m_viewParser.getModelLowerBounds()
        bounds_max = self.m_viewParser.getModelUpperBounds()
        if not math.isnan(bounds_min.x()) and not math.isnan(bounds_max.x()):
            self.spnHmX.setValue(bounds_min.x())
            self.spnHmY.setValue(bounds_min.y())
            self.spnHmW.setValue(max(1.0, bounds_max.x() - bounds_min.x()))
            self.spnHmH.setValue(max(1.0, bounds_max.y() - bounds_min.y()))
            self._update_heightmap_drawers()

    def _on_hm_table_edited(self):
        self._update_heightmap_drawers()

    def _on_hm_use_toggled(self, checked: bool):
        if checked:
            self.logWidget.appendLog("Heightmap transformation enabled.", "INFO")
        else:
            self.logWidget.appendLog("Heightmap transformation disabled.", "INFO")

    def startProbing(self):
        rect = QRectF(self.spnHmX.value(), self.spnHmY.value(), self.spnHmW.value(), self.spnHmH.value())
        gx = self.spnHmGridX.value()
        gy = self.spnHmGridY.value()
        zt = self.spnHmZTop.value()
        zb = self.spnHmZBottom.value()
        pf = self.spnHmFeed.value()

        self.m_heightMapModel.resize(gx, gy)
        probe_cmds = HeightMapManager.generateProbeProgram(rect, gx, gy, zt, zb, pf, self.m_wpos.x(), self.m_wpos.y())

        self.m_isProbing = True
        self.m_probeIndex = 0

        self.m_probeModel.clear()
        self.m_probeModel.insertCommands(0, probe_cmds)

        # Stream probing routine
        self.m_queue.clear()
        self.m_queue.extend(probe_cmds)
        self.m_queueCommandIndex = 0
        self.m_bufferLength.clear()
        self.m_senderState = SenderState.Transferring

        self._feed_stream_queue()

    def openSettings(self):
        dlg = SettingsDialog(self.m_storage, self.m_profileManager, self)
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            self._apply_settings()
            self._setup_connection()

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.KeyPress and self.chkJogKeyboard.isChecked():
            key = event.key()
            if key == Qt.Key.Key_Left:
                self.jogAxis("X", -1); return True
            elif key == Qt.Key.Key_Right:
                self.jogAxis("X", 1); return True
            elif key == Qt.Key.Key_Up:
                self.jogAxis("Y", 1); return True
            elif key == Qt.Key.Key_Down:
                self.jogAxis("Y", -1); return True
            elif key == Qt.Key.Key_PageUp:
                self.jogAxis("Z", 1); return True
            elif key == Qt.Key.Key_PageDown:
                self.jogAxis("Z", -1); return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if self.m_connection and self.m_connection.isConnected():
            self.m_connection.close()
        self.m_storage.sync()
        event.accept()

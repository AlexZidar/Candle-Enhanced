"""Visual Block-Code Macro Builder Dialog and Editor."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QGroupBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QTextEdit, QMessageBox, QColorDialog
)
from candle.models.macro_model import Macro, MacroBlock, BlockType, MacroManager


class BlockCardWidget(QFrame):
    """Visual card displaying a single macro action block with parameters and controls."""
    movedUp = pyqtSignal()
    movedDown = pyqtSignal()
    deleted = pyqtSignal()
    changed = pyqtSignal()

    def __init__(self, index: int, block: MacroBlock, parent=None):
        super().__init__(parent)
        self.m_index = index
        self.m_block = block

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "BlockCardWidget { background-color: #2b2b2b; border: 1px solid #444; border-radius: 6px; padding: 6px; } "
            "BlockCardWidget:hover { border-color: #1976d2; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Header Row: Badge, Title, Up/Down/Delete
        hdr = QHBoxLayout()
        lbl_badge = QLabel(f"<b>#{index + 1}</b>", self)
        lbl_badge.setStyleSheet("background: #1976d2; color: white; border-radius: 3px; padding: 2px 6px; font-size: 11px;")
        
        lbl_title = QLabel(f"<b>{self._get_title()}</b>", self)
        lbl_title.setStyleSheet("font-size: 12px; color: #ffffff;")

        self.btnUp = QPushButton("▲", self)
        self.btnUp.setFixedSize(24, 24)
        self.btnUp.setToolTip("Move Step Up")
        self.btnUp.clicked.connect(self.movedUp.emit)

        self.btnDown = QPushButton("▼", self)
        self.btnDown.setFixedSize(24, 24)
        self.btnDown.setToolTip("Move Step Down")
        self.btnDown.clicked.connect(self.movedDown.emit)

        self.btnDel = QPushButton("✖", self)
        self.btnDel.setFixedSize(24, 24)
        self.btnDel.setToolTip("Delete Step")
        self.btnDel.setStyleSheet("color: #ff5252;")
        self.btnDel.clicked.connect(self.deleted.emit)

        hdr.addWidget(lbl_badge)
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        hdr.addWidget(self.btnUp)
        hdr.addWidget(self.btnDown)
        hdr.addWidget(self.btnDel)
        layout.addLayout(hdr)

        # Body: Parameter controls based on block type
        self._build_param_controls(layout)

    def _get_title(self) -> str:
        bt = self.m_block.block_type
        titles = {
            BlockType.HOME: "🏠 Home Machine ($H)",
            BlockType.UNLOCK: "🔓 Unlock Controller ($X)",
            BlockType.SAFE_Z: "⬆ Safe Top Z Retract",
            BlockType.MOVE_TO: "📍 Move to Coordinates",
            BlockType.MOVE_RELATIVE: "↗ Relative Move",
            BlockType.ZERO_AXIS: "🎯 Zero Axes (G92)",
            BlockType.PROBE_Z: "🔍 Touch Probe & Zero Z",
            BlockType.SPINDLE: "⚡ Spindle Control",
            BlockType.COOLANT: "💧 Coolant Control",
            BlockType.DWELL: "⏱ Pause / Dwell",
            BlockType.PROMPT: "💬 User Confirmation Prompt",
            BlockType.CUSTOM_GCODE: "📝 Custom G-Code",
            BlockType.RUN_FILE: "▶ Begin Loaded G-Code File"
        }
        return titles.get(bt, str(bt.value))

    def _build_param_controls(self, layout: QVBoxLayout):
        bt = self.m_block.block_type
        p = self.m_block.params

        if bt == BlockType.SAFE_Z:
            row = QHBoxLayout()
            row.addWidget(QLabel("Clearance below top limit (mm):"))
            spn = QDoubleSpinBox(self)
            spn.setRange(0.5, 50.0)
            spn.setValue(float(p.get("clearance", 3.0)))
            spn.valueChanged.connect(lambda v: self._set_param("clearance", v))
            row.addWidget(spn)
            row.addStretch()
            layout.addLayout(row)

        elif bt == BlockType.MOVE_TO:
            grid = QGridLayout()
            spn_x = QDoubleSpinBox(self); spn_x.setRange(-5000, 5000); spn_x.setValue(float(p.get("x", 0.0)))
            spn_x.valueChanged.connect(lambda v: self._set_param("x", v))
            spn_y = QDoubleSpinBox(self); spn_y.setRange(-5000, 5000); spn_y.setValue(float(p.get("y", 0.0)))
            spn_y.valueChanged.connect(lambda v: self._set_param("y", v))
            
            chk_z = QCheckBox("Set Z:", self)
            spn_z = QDoubleSpinBox(self); spn_z.setRange(-500, 500); spn_z.setValue(float(p.get("z", 0.0) or 0.0))
            spn_z.setEnabled("z" in p and p["z"] is not None)
            chk_z.setChecked("z" in p and p["z"] is not None)
            
            def _on_chk_z(ch):
                spn_z.setEnabled(ch)
                self._set_param("z", spn_z.value() if ch else None)
            chk_z.toggled.connect(_on_chk_z)
            spn_z.valueChanged.connect(lambda v: self._set_param("z", v if chk_z.isChecked() else None))

            spn_f = QSpinBox(self); spn_f.setRange(1, 20000); spn_f.setValue(int(p.get("feed", 1000)))
            spn_f.valueChanged.connect(lambda v: self._set_param("feed", v))

            cbo_coord = QComboBox(self)
            cbo_coord.addItems(["Work Coordinates (WPos)", "Machine Coordinates (G53)"])
            cbo_coord.setCurrentIndex(1 if p.get("coords") == "machine" else 0)
            cbo_coord.currentIndexChanged.connect(lambda idx: self._set_param("coords", "machine" if idx == 1 else "work"))

            grid.addWidget(QLabel("X:"), 0, 0); grid.addWidget(spn_x, 0, 1)
            grid.addWidget(QLabel("Y:"), 0, 2); grid.addWidget(spn_y, 0, 3)
            grid.addWidget(chk_z, 1, 0); grid.addWidget(spn_z, 1, 1)
            grid.addWidget(QLabel("Feed (mm/min):"), 1, 2); grid.addWidget(spn_f, 1, 3)
            grid.addWidget(QLabel("System:"), 2, 0); grid.addWidget(cbo_coord, 2, 1, 1, 3)
            layout.addLayout(grid)

        elif bt == BlockType.MOVE_RELATIVE:
            row = QHBoxLayout()
            spn_dx = QDoubleSpinBox(self); spn_dx.setRange(-1000, 1000); spn_dx.setValue(float(p.get("dx", 0.0)))
            spn_dx.valueChanged.connect(lambda v: self._set_param("dx", v))
            spn_dy = QDoubleSpinBox(self); spn_dy.setRange(-1000, 1000); spn_dy.setValue(float(p.get("dy", 0.0)))
            spn_dy.valueChanged.connect(lambda v: self._set_param("dy", v))
            spn_dz = QDoubleSpinBox(self); spn_dz.setRange(-1000, 1000); spn_dz.setValue(float(p.get("dz", 0.0)))
            spn_dz.valueChanged.connect(lambda v: self._set_param("dz", v))
            spn_f = QSpinBox(self); spn_f.setRange(1, 20000); spn_f.setValue(int(p.get("feed", 500)))
            spn_f.valueChanged.connect(lambda v: self._set_param("feed", v))

            row.addWidget(QLabel("ΔX:")); row.addWidget(spn_dx)
            row.addWidget(QLabel("ΔY:")); row.addWidget(spn_dy)
            row.addWidget(QLabel("ΔZ:")); row.addWidget(spn_dz)
            row.addWidget(QLabel("Feed:")); row.addWidget(spn_f)
            layout.addLayout(row)

        elif bt == BlockType.ZERO_AXIS:
            row = QHBoxLayout()
            axes = p.get("axes", ["X", "Y", "Z"])
            chk_x = QCheckBox("X", self); chk_x.setChecked("X" in axes)
            chk_y = QCheckBox("Y", self); chk_y.setChecked("Y" in axes)
            chk_z = QCheckBox("Z", self); chk_z.setChecked("Z" in axes)
            chk_a = QCheckBox("A", self); chk_a.setChecked("A" in axes)

            def _update_axes():
                active = []
                if chk_x.isChecked(): active.append("X")
                if chk_y.isChecked(): active.append("Y")
                if chk_z.isChecked(): active.append("Z")
                if chk_a.isChecked(): active.append("A")
                self._set_param("axes", active)

            chk_x.toggled.connect(_update_axes)
            chk_y.toggled.connect(_update_axes)
            chk_z.toggled.connect(_update_axes)
            chk_a.toggled.connect(_update_axes)

            row.addWidget(QLabel("Zero Work Axes:"))
            row.addWidget(chk_x); row.addWidget(chk_y); row.addWidget(chk_z); row.addWidget(chk_a)
            row.addStretch()
            layout.addLayout(row)

        elif bt == BlockType.PROBE_Z:
            grid = QGridLayout()
            spn_t = QDoubleSpinBox(self); spn_t.setRange(0.01, 100.0); spn_t.setValue(float(p.get("thickness", 15.0)))
            spn_t.valueChanged.connect(lambda v: self._set_param("thickness", v))
            spn_d = QDoubleSpinBox(self); spn_d.setRange(1.0, 200.0); spn_d.setValue(float(p.get("distance", 30.0)))
            spn_d.valueChanged.connect(lambda v: self._set_param("distance", v))
            spn_sf = QDoubleSpinBox(self); spn_sf.setRange(1.0, 500.0); spn_sf.setValue(float(p.get("search_feed", 40.0)))
            spn_sf.valueChanged.connect(lambda v: self._set_param("search_feed", v))
            spn_lf = QDoubleSpinBox(self); spn_lf.setRange(1.0, 200.0); spn_lf.setValue(float(p.get("latch_feed", 10.0)))
            spn_lf.valueChanged.connect(lambda v: self._set_param("latch_feed", v))
            spn_r = QDoubleSpinBox(self); spn_r.setRange(0.5, 50.0); spn_r.setValue(float(p.get("retract", 5.0)))
            spn_r.valueChanged.connect(lambda v: self._set_param("retract", v))

            grid.addWidget(QLabel("Plate Thickness (mm):"), 0, 0); grid.addWidget(spn_t, 0, 1)
            grid.addWidget(QLabel("Max Search Distance:"), 0, 2); grid.addWidget(spn_d, 0, 3)
            grid.addWidget(QLabel("Search Feed:"), 1, 0); grid.addWidget(spn_sf, 1, 1)
            grid.addWidget(QLabel("Latch Feed:"), 1, 2); grid.addWidget(spn_lf, 1, 3)
            grid.addWidget(QLabel("Retract Height:"), 2, 0); grid.addWidget(spn_r, 2, 1)
            layout.addLayout(grid)

        elif bt == BlockType.SPINDLE:
            row = QHBoxLayout()
            cbo_state = QComboBox(self); cbo_state.addItems(["CW (M3)", "CCW (M4)", "STOP (M5)"])
            curr_state = p.get("state", "CW")
            cbo_state.setCurrentIndex(2 if curr_state == "STOP" else (1 if curr_state == "CCW" else 0))
            
            spn_rpm = QSpinBox(self); spn_rpm.setRange(0, 100000); spn_rpm.setValue(int(p.get("rpm", 8000)))
            spn_delay = QDoubleSpinBox(self); spn_delay.setRange(0.0, 30.0); spn_delay.setValue(float(p.get("delay", 2.0)))

            def _on_spindle_state(idx):
                st = "STOP" if idx == 2 else ("CCW" if idx == 1 else "CW")
                spn_rpm.setEnabled(st != "STOP")
                spn_delay.setEnabled(st != "STOP")
                self._set_param("state", st)

            cbo_state.currentIndexChanged.connect(_on_spindle_state)
            spn_rpm.valueChanged.connect(lambda v: self._set_param("rpm", v))
            spn_delay.valueChanged.connect(lambda v: self._set_param("delay", v))

            row.addWidget(QLabel("Action:")); row.addWidget(cbo_state)
            row.addWidget(QLabel("RPM:")); row.addWidget(spn_rpm)
            row.addWidget(QLabel("Spinup Delay (s):")); row.addWidget(spn_delay)
            row.addStretch()
            layout.addLayout(row)

        elif bt == BlockType.DWELL:
            row = QHBoxLayout()
            row.addWidget(QLabel("Wait Duration (seconds):"))
            spn_s = QDoubleSpinBox(self); spn_s.setRange(0.1, 300.0); spn_s.setValue(float(p.get("seconds", 2.0)))
            spn_s.valueChanged.connect(lambda v: self._set_param("seconds", v))
            row.addWidget(spn_s)
            row.addStretch()
            layout.addLayout(row)

        elif bt == BlockType.PROMPT:
            txt_msg = QLineEdit(self)
            txt_msg.setText(str(p.get("message", "Ready to proceed to next step?")))
            txt_msg.textChanged.connect(lambda t: self._set_param("message", t))
            layout.addWidget(QLabel("Message Prompt for User:"))
            layout.addWidget(txt_msg)

        elif bt == BlockType.CUSTOM_GCODE:
            txt_code = QTextEdit(self)
            txt_code.setFixedHeight(60)
            txt_code.setText(str(p.get("code", "G0 X0 Y0")))
            txt_code.textChanged.connect(lambda: self._set_param("code", txt_code.toPlainText()))
            layout.addWidget(QLabel("G-Code Commands (one per line):"))
            layout.addWidget(txt_code)

    def _set_param(self, key: str, val):
        self.m_block.params[key] = val
        self.changed.emit()


class MacroBuilderDialog(QDialog):
    """Full visual Block-Code Macro Builder and Manager."""

    def __init__(self, macro_manager: MacroManager, macro_runner=None, parent=None):
        super().__init__(parent)
        self.m_manager = macro_manager
        self.m_runner = macro_runner
        self.m_currentMacro: Optional[Macro] = None

        self.setWindowTitle("Custom Macros & Command Chain Builder")
        self.resize(900, 650)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Left Panel: Macro List & Management
        left_pane = QWidget(self)
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        lbl_macros = QLabel("<b>My Macros</b>", left_pane)
        self.lstMacros = QListWidget(left_pane)
        self.lstMacros.currentRowChanged.connect(self._on_macro_selected)

        btn_row_m = QHBoxLayout()
        self.btnNewMacro = QPushButton("+ New", left_pane)
        self.btnNewMacro.clicked.connect(self._on_new_macro)
        self.btnDupMacro = QPushButton("Duplicate", left_pane)
        self.btnDupMacro.clicked.connect(self._on_dup_macro)
        self.btnDelMacro = QPushButton("Delete", left_pane)
        self.btnDelMacro.setStyleSheet("color: #ff5252;")
        self.btnDelMacro.clicked.connect(self._on_del_macro)

        btn_row_m.addWidget(self.btnNewMacro)
        btn_row_m.addWidget(self.btnDupMacro)
        btn_row_m.addWidget(self.btnDelMacro)

        left_layout.addWidget(lbl_macros)
        left_layout.addWidget(self.lstMacros, stretch=1)
        left_layout.addLayout(btn_row_m)
        left_pane.setFixedWidth(240)
        main_layout.addWidget(left_pane)

        # Right Panel: Visual Block-Code Editor
        right_pane = QWidget(self)
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Macro Header: Name & Color
        hdr_box = QGroupBox("Macro Properties", right_pane)
        hdr_layout = QHBoxLayout(hdr_box)
        
        hdr_layout.addWidget(QLabel("Name:"))
        self.txtName = QLineEdit(hdr_box)
        self.txtName.textChanged.connect(self._on_name_changed)
        hdr_layout.addWidget(self.txtName, stretch=1)

        self.btnColor = QPushButton("Button Color", hdr_box)
        self.btnColor.setFixedWidth(110)
        self.btnColor.clicked.connect(self._on_pick_color)
        hdr_layout.addWidget(self.btnColor)
        right_layout.addWidget(hdr_box)

        # Center: Step-by-Step Block Chain Area
        lbl_chain = QLabel("<b>Command Chain Execution Flow:</b>", right_pane)
        right_layout.addWidget(lbl_chain)

        self.scrollBlocks = QScrollArea(right_pane)
        self.scrollBlocks.setWidgetResizable(True)
        self.scrollBlocks.setFrameShape(QFrame.Shape.NoFrame)
        self.wgtBlocksContainer = QWidget()
        self.layoutBlocks = QVBoxLayout(self.wgtBlocksContainer)
        self.layoutBlocks.setContentsMargins(4, 4, 4, 4)
        self.layoutBlocks.setSpacing(6)
        self.scrollBlocks.setWidget(self.wgtBlocksContainer)
        right_layout.addWidget(self.scrollBlocks, stretch=1)

        # Action Palette: + Add Action Blocks
        grp_add = QGroupBox("+ Add Action Block to Chain", right_pane)
        grid_add = QGridLayout(grp_add)
        grid_add.setContentsMargins(6, 6, 6, 6)
        grid_add.setSpacing(4)

        blocks_defs = [
            ("🏠 Home Machine", BlockType.HOME, {}),
            ("🔓 Unlock ($X)", BlockType.UNLOCK, {}),
            ("⬆ Safe Top Z", BlockType.SAFE_Z, {"clearance": 3.0}),
            ("📍 Move To Coords", BlockType.MOVE_TO, {"x": 0.0, "y": 0.0, "feed": 1000, "coords": "work"}),
            ("↗ Relative Move", BlockType.MOVE_RELATIVE, {"dx": 0.0, "dy": 0.0, "dz": 0.0, "feed": 500}),
            ("🎯 Zero Axes", BlockType.ZERO_AXIS, {"axes": ["X", "Y", "Z"]}),
            ("🔍 Probe & Zero Z", BlockType.PROBE_Z, {"thickness": 15.0, "distance": 30.0, "search_feed": 40.0, "latch_feed": 10.0, "retract": 5.0}),
            ("⚡ Spindle Start/Stop", BlockType.SPINDLE, {"state": "CW", "rpm": 8000, "delay": 2.0}),
            ("⏱ Pause / Dwell", BlockType.DWELL, {"seconds": 2.0}),
            ("💬 User Prompt", BlockType.PROMPT, {"message": "Attach touch plate and clip. Proceed?"}),
            ("📝 Custom G-Code", BlockType.CUSTOM_GCODE, {"code": "G0 X0 Y0"}),
            ("▶ Run Loaded File", BlockType.RUN_FILE, {}),
        ]

        for i, (title, btype, def_params) in enumerate(blocks_defs):
            r, c = divmod(i, 4)
            btn = QPushButton(title, grp_add)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda ch, bt=btype, p=def_params: self._add_block(bt, p))
            grid_add.addWidget(btn, r, c)

        right_layout.addWidget(grp_add)

        # Bottom Bar: Run / Test & Save
        bot_bar = QHBoxLayout()
        self.btnRunTest = QPushButton("▶ Run / Test Macro", right_pane)
        self.btnRunTest.setStyleSheet("font-weight: bold; background: #1976d2; color: white; min-height: 28px;")
        self.btnRunTest.clicked.connect(self._on_run_test)

        self.btnSaveClose = QPushButton("Save & Close", right_pane)
        self.btnSaveClose.setStyleSheet("font-weight: bold; background: #2e7d32; color: white; min-height: 28px;")
        self.btnSaveClose.clicked.connect(self._on_save_close)

        bot_bar.addWidget(self.btnRunTest)
        bot_bar.addStretch()
        bot_bar.addWidget(self.btnSaveClose)
        right_layout.addLayout(bot_bar)

        main_layout.addWidget(right_pane, stretch=1)

        self._refresh_macro_list()
        if self.m_manager.macros():
            self.lstMacros.setCurrentRow(0)

    def _refresh_macro_list(self):
        self.lstMacros.blockSignals(True)
        self.lstMacros.clear()
        for m in self.m_manager.macros():
            item = QListWidgetItem(m.name)
            self.lstMacros.addItem(item)
        self.lstMacros.blockSignals(False)

    def _on_macro_selected(self, row: int):
        if 0 <= row < len(self.m_manager.macros()):
            self.m_currentMacro = self.m_manager.macros()[row]
            self.txtName.setText(self.m_currentMacro.name)
            self._update_color_btn(self.m_currentMacro.color)
            self._rebuild_blocks_view()

    def _update_color_btn(self, color_hex: str):
        self.btnColor.setStyleSheet(f"background-color: {color_hex}; color: white; font-weight: bold;")

    def _on_name_changed(self, name: str):
        if self.m_currentMacro:
            self.m_currentMacro.name = name
            curr_row = self.lstMacros.currentRow()
            if 0 <= curr_row < self.lstMacros.count():
                self.lstMacros.item(curr_row).setText(name)

    def _on_pick_color(self):
        if not self.m_currentMacro:
            return
        c = QColorDialog.getColor(QColor(self.m_currentMacro.color), self, "Pick Macro Button Color")
        if c.isValid():
            self.m_currentMacro.color = c.name()
            self._update_color_btn(c.name())

    def _on_new_macro(self):
        new_m = Macro(name="New Command Chain", color="#1976d2", blocks=[])
        self.m_manager.add_macro(new_m)
        self._refresh_macro_list()
        self.lstMacros.setCurrentRow(self.lstMacros.count() - 1)

    def _on_dup_macro(self):
        if not self.m_currentMacro:
            return
        dup_dict = self.m_currentMacro.to_dict()
        dup_dict["id"] = None
        dup_dict["name"] = f"{self.m_currentMacro.name} (Copy)"
        dup_m = Macro.from_dict(dup_dict)
        self.m_manager.add_macro(dup_m)
        self._refresh_macro_list()
        self.lstMacros.setCurrentRow(self.lstMacros.count() - 1)

    def _on_del_macro(self):
        if not self.m_currentMacro:
            return
        if len(self.m_manager.macros()) <= 1:
            QMessageBox.information(self, "Cannot Delete", "You must keep at least one macro.")
            return
        res = QMessageBox.question(self, "Confirm Delete", f"Delete macro '{self.m_currentMacro.name}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            self.m_manager.remove_macro(self.m_currentMacro.id)
            self._refresh_macro_list()
            self.lstMacros.setCurrentRow(0)

    def _add_block(self, btype: BlockType, def_params: dict):
        if not self.m_currentMacro:
            return
        import copy
        block = MacroBlock(block_type=btype, params=copy.deepcopy(def_params))
        self.m_currentMacro.blocks.append(block)
        self._rebuild_blocks_view()

    def _rebuild_blocks_view(self):
        # Clear previous block cards
        while self.layoutBlocks.count():
            item = self.layoutBlocks.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.m_currentMacro or not self.m_currentMacro.blocks:
            lbl_empty = QLabel("<i>No action blocks added yet. Click an action button below to add steps.</i>", self.wgtBlocksContainer)
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: #888888; padding: 20px;")
            self.layoutBlocks.addWidget(lbl_empty)
            return

        for idx, block in enumerate(self.m_currentMacro.blocks):
            card = BlockCardWidget(idx, block, self.wgtBlocksContainer)
            card.movedUp.connect(lambda i=idx: self._move_block(i, -1))
            card.movedDown.connect(lambda i=idx: self._move_block(i, 1))
            card.deleted.connect(lambda i=idx: self._delete_block(i))
            self.layoutBlocks.addWidget(card)

            # Add flow arrow indicator between blocks
            if idx < len(self.m_currentMacro.blocks) - 1:
                lbl_arrow = QLabel("⬇", self.wgtBlocksContainer)
                lbl_arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_arrow.setStyleSheet("color: #1976d2; font-size: 14px; font-weight: bold;")
                self.layoutBlocks.addWidget(lbl_arrow)

        self.layoutBlocks.addStretch()

    def _move_block(self, index: int, delta: int):
        if not self.m_currentMacro:
            return
        new_idx = index + delta
        if 0 <= new_idx < len(self.m_currentMacro.blocks):
            b = self.m_currentMacro.blocks.pop(index)
            self.m_currentMacro.blocks.insert(new_idx, b)
            self._rebuild_blocks_view()

    def _delete_block(self, index: int):
        if not self.m_currentMacro:
            return
        if 0 <= index < len(self.m_currentMacro.blocks):
            self.m_currentMacro.blocks.pop(index)
            self._rebuild_blocks_view()

    def _on_run_test(self):
        if not self.m_currentMacro:
            return
        if self.m_runner:
            self.m_manager.save()
            self.m_runner.runMacro(self.m_currentMacro)

    def _on_save_close(self):
        self.m_manager.save()
        self.accept()

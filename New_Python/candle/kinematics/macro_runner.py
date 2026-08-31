"""MacroRunner: Synchronous/Asynchronous state-machine command-chain executor for block-code macros."""

import time
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from typing import Optional, List
from candle.models.macro_model import Macro, MacroBlock, BlockType
from candle.config import DeviceState


class MacroRunner(QObject):
    stepStarted = pyqtSignal(int, str)
    stepCompleted = pyqtSignal(int)
    macroFinished = pyqtSignal(bool, str)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.m_window = main_window
        self.m_currentMacro: Optional[Macro] = None
        self.m_currentStepIndex: int = -1
        self.m_isRunning: bool = False

        # Synchronization State
        self.m_waitingForMotion: bool = False
        self.m_motionStarted: bool = False
        self.m_stepSendTime: float = 0.0

        # Probe State
        self.m_waitingForProbe: bool = False
        self.m_probeStage: int = 0
        self.m_probeParams: dict = {}

        # Watchdog Timeout Timer
        self.m_watchdogTimer = QTimer(self)
        self.m_watchdogTimer.setSingleShot(True)
        self.m_watchdogTimer.timeout.connect(self._on_watchdog_timeout)

    def isRunning(self) -> bool:
        return self.m_isRunning

    def runMacro(self, macro: Macro) -> None:
        if self.m_isRunning:
            self.m_window.logWidget.appendLog("A macro is already running.", "WARN")
            return

        if not macro.blocks:
            self.m_window.logWidget.appendLog(f"Macro '{macro.name}' has no blocks.", "WARN")
            return

        if not self.m_window.m_connection or not self.m_window.m_connection.isConnected():
            self.m_window.logWidget.appendLog("Cannot run macro: Controller is not connected.", "ERROR")
            self.macroFinished.emit(False, "Controller not connected")
            return

        self.m_currentMacro = macro
        self.m_currentStepIndex = 0
        self.m_isRunning = True
        self.m_waitingForMotion = False
        self.m_waitingForProbe = False

        self.m_window.logWidget.appendLog(f"▶ Starting Macro: '{macro.name}' ({len(macro.blocks)} steps)", "INFO")
        self.m_window.txtConsole.append(
            f"<span style='color:#2196f3; font-weight:bold;'>[MACRO START] '{macro.name}' ({len(macro.blocks)} steps)</span>"
        )

        self._execute_current_step()

    def abort(self) -> None:
        if not self.m_isRunning:
            return
        self.m_isRunning = False
        self.m_waitingForMotion = False
        self.m_waitingForProbe = False
        self.m_watchdogTimer.stop()
        self.m_window.sendCommand("!")
        self.m_window.logWidget.appendLog("Macro execution aborted by user.", "WARN")
        self.m_window.txtConsole.append("<span style='color:red; font-weight:bold;'>[MACRO ABORTED]</span>")
        self.macroFinished.emit(False, "Aborted by user")

    def onDeviceStateChanged(self, state: DeviceState) -> None:
        if not self.m_isRunning:
            return

        if state == DeviceState.Alarm:
            # Alarm occurred
            self.m_window.logWidget.appendLog("Macro Aborted: Controller entered Alarm state.", "ERROR")
            self.abort()
            return

        if self.m_waitingForMotion:
            if state in (DeviceState.Home, DeviceState.Run, DeviceState.Jog):
                self.m_motionStarted = True
            elif state == DeviceState.Idle:
                if self.m_motionStarted:
                    # Motion was seen and is now finished
                    self.m_waitingForMotion = False
                    self.m_watchdogTimer.stop()
                    QTimer.singleShot(150, self._advance_step)
                else:
                    # Motion may have been instantaneous; allow settling check
                    if time.time() - self.m_stepSendTime >= 0.5:
                        self.m_waitingForMotion = False
                        self.m_watchdogTimer.stop()
                        QTimer.singleShot(100, self._advance_step)

    def _execute_current_step(self) -> None:
        if not self.m_isRunning or not self.m_currentMacro:
            return

        if self.m_currentStepIndex >= len(self.m_currentMacro.blocks):
            self._finish_macro(True, "Macro completed successfully")
            return

        block = self.m_currentMacro.blocks[self.m_currentStepIndex]
        desc = block.description()
        self.stepStarted.emit(self.m_currentStepIndex, desc)
        self.m_window.logWidget.appendLog(
            f"Executing Step [{self.m_currentStepIndex + 1}/{len(self.m_currentMacro.blocks)}]: {desc}", "INFO"
        )

        bt = block.block_type
        params = block.params

        if bt == BlockType.HOME:
            self.m_window.sendCommand("$H")
            self._wait_for_motion(timeout_sec=90)

        elif bt == BlockType.UNLOCK:
            self.m_window.sendCommand("$X")
            QTimer.singleShot(250, self._advance_step)

        elif bt == BlockType.SAFE_Z:
            c = float(params.get("clearance", 3.0))
            self.m_window.sendCommand(f"G53 G0 Z-{c:.3f}")
            self._wait_for_motion(timeout_sec=30)

        elif bt == BlockType.MOVE_TO:
            x = float(params.get("x", 0.0))
            y = float(params.get("y", 0.0))
            z = params.get("z", None)
            f = int(params.get("feed", 1000))
            coord = params.get("coords", "work")

            prefix = "G53 " if coord == "machine" else "G90 "
            z_cmd = f" Z{float(z):.3f}" if (z is not None and z != "") else ""
            cmd = f"{prefix}G0 X{x:.3f} Y{y:.3f}{z_cmd} F{f}"
            self.m_window.sendCommand(cmd)
            self._wait_for_motion(timeout_sec=60)

        elif bt == BlockType.MOVE_RELATIVE:
            dx = float(params.get("dx", 0.0))
            dy = float(params.get("dy", 0.0))
            dz = float(params.get("dz", 0.0))
            f = int(params.get("feed", 500))
            self.m_window.sendCommand(f"G91 G0 X{dx:.3f} Y{dy:.3f} Z{dz:.3f} F{f}")
            self.m_window.sendCommand("G90")
            self._wait_for_motion(timeout_sec=30)

        elif bt == BlockType.ZERO_AXIS:
            axes = params.get("axes", ["X", "Y", "Z"])
            zero_str = " ".join(f"{a}0" for a in axes)
            self.m_window.sendCommand(f"G92 {zero_str}")
            QTimer.singleShot(250, self._advance_step)

        elif bt == BlockType.PROBE_Z:
            self._start_probe_step(params)

        elif bt == BlockType.SPINDLE:
            state = params.get("state", "CW")
            rpm = params.get("rpm", 8000)
            delay = float(params.get("delay", 2.0))

            if state == "STOP":
                self.m_window.sendCommand("M5")
                QTimer.singleShot(200, self._advance_step)
            else:
                m_code = "M3" if state == "CW" else "M4"
                self.m_window.sendCommand(f"{m_code} S{int(rpm)}")
                # Delay for spindle spinup
                QTimer.singleShot(int(delay * 1000), self._advance_step)

        elif bt == BlockType.COOLANT:
            state = params.get("state", "FLOOD")
            if state == "FLOOD":
                self.m_window.sendCommand("M8")
            elif state == "MIST":
                self.m_window.sendCommand("M7")
            else:
                self.m_window.sendCommand("M9")
            QTimer.singleShot(200, self._advance_step)

        elif bt == BlockType.DWELL:
            secs = float(params.get("seconds", 2.0))
            self.m_window.sendCommand(f"G4 P{secs:.2f}")
            QTimer.singleShot(int(secs * 1000) + 100, self._advance_step)

        elif bt == BlockType.PROMPT:
            msg = params.get("message", "Ready to proceed to next step?")
            res = QMessageBox.question(
                self.m_window,
                "Macro Prompt",
                msg,
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Ok
            )
            if res == QMessageBox.StandardButton.Ok:
                self._advance_step()
            else:
                self.abort()

        elif bt == BlockType.CUSTOM_GCODE:
            code = params.get("code", "")
            for line in code.strip().split("\n"):
                l = line.strip()
                if l:
                    self.m_window.sendCommand(l)
            self._wait_for_motion(timeout_sec=30)

        elif bt == BlockType.RUN_FILE:
            if self.m_window.m_programModel.rowCount() == 0:
                self.m_window.logWidget.appendLog("Macro Warning: No G-code file loaded to run.", "WARN")
                QMessageBox.warning(self.m_window, "No File Loaded", "Cannot run file: No G-code program is currently loaded.")
                self.abort()
                return

            self.m_window.logWidget.appendLog("Starting G-code file streaming from Macro.", "INFO")
            self.m_window.startStreaming()
            self._finish_macro(True, "G-code file execution initiated")

    def _wait_for_motion(self, timeout_sec: int = 45) -> None:
        self.m_waitingForMotion = True
        self.m_motionStarted = False
        self.m_stepSendTime = time.time()
        self.m_watchdogTimer.start(int(timeout_sec * 1000))

    def _start_probe_step(self, params: dict) -> None:
        self.m_probeParams = params
        self.m_waitingForProbe = True
        self.m_probeStage = 1

        dist = float(params.get("distance", 30.0))
        feed = float(params.get("search_feed", 40.0))

        # Fast search probe
        self.m_window.sendCommand("G21 G91")
        self.m_window.sendCommand(f"G38.2 Z-{dist:.3f} F{feed:.0f}")
        self.m_watchdogTimer.start(45000)

    def onProbeReportReceived(self, z_val: float, succ: bool) -> None:
        if not self.m_waitingForProbe:
            return

        if not succ:
            self.m_waitingForProbe = False
            self.m_watchdogTimer.stop()
            self.m_window.logWidget.appendLog("Touch plate contact not detected during probe.", "ERROR")
            self.m_window.txtConsole.append("<span style='color:red; font-weight:bold;'>[PROBE FAILED] No contact detected.</span>")
            self.abort()
            return

        if self.m_probeStage == 1:
            # First search contact made -> lift 1.5mm and perform slow latch probe
            self.m_probeStage = 2
            latch_feed = float(self.m_probeParams.get("latch_feed", 10.0))
            self.m_window.sendCommand("G91 G0 Z1.500")
            self.m_window.sendCommand(f"G38.2 Z-3.000 F{latch_feed:.0f}")

        elif self.m_probeStage == 2:
            # Latch contact made -> set Z zero to plate thickness and retract
            self.m_waitingForProbe = False
            self.m_watchdogTimer.stop()
            thickness = float(self.m_probeParams.get("thickness", 15.0))
            retract = float(self.m_probeParams.get("retract", 5.0))

            self.m_window.sendCommand("G90")
            self.m_window.sendCommand(f"G92 Z{thickness:.3f}")
            self.m_window.sendCommand(f"G91 G0 Z{retract:.3f}")
            self.m_window.sendCommand("G90")

            self.m_window.logWidget.appendLog(
                f"Z-Zero set using touch plate ({thickness:.2f}mm). Retracted {retract:.1f}mm.", "INFO"
            )
            self.m_window.txtConsole.append(
                f"<span style='color:#4caf50; font-weight:bold;'>[Z-PROBE SUCCESS] Work Z set to {thickness:.3f}mm. Retracted {retract:.1f}mm.</span>"
            )

            self._wait_for_motion(timeout_sec=10)

    def _on_watchdog_timeout(self) -> None:
        if self.m_isRunning:
            self.m_window.logWidget.appendLog("Macro Step Timeout: Motion did not complete within expected time.", "WARN")
            self._advance_step()

    def _advance_step(self) -> None:
        if not self.m_isRunning:
            return
        self.m_waitingForMotion = False
        self.m_waitingForProbe = False
        self.m_watchdogTimer.stop()
        self.stepCompleted.emit(self.m_currentStepIndex)
        self.m_currentStepIndex += 1
        self._execute_current_step()

    def _finish_macro(self, success: bool, msg: str) -> None:
        self.m_isRunning = False
        self.m_waitingForMotion = False
        self.m_waitingForProbe = False
        self.m_watchdogTimer.stop()
        self.m_currentMacro = None
        self.m_currentStepIndex = -1
        self.macroFinished.emit(success, msg)
        self.m_window.logWidget.appendLog(f"✔ Macro Completed: {msg}", "INFO")
        self.m_window.txtConsole.append(f"<span style='color:#4caf50; font-weight:bold;'>[MACRO COMPLETE] {msg}</span>")

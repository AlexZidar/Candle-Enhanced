"""PySerial-based GRBL serial connection with background read thread."""

import threading
import time
from typing import Union, Optional, List
import serial
import serial.tools.list_ports
from PyQt6.QtCore import pyqtSignal
from .base import Connection


class SerialPortConnection(Connection):
    def __init__(self, port_name: str = "", baud_rate: int = 115200, parent=None):
        super().__init__(parent)
        self.m_portName: str = port_name
        self.m_baudRate: int = baud_rate
        self.m_serial: Optional[serial.Serial] = None
        self.m_running: bool = False
        self.m_thread: Optional[threading.Thread] = None
        self.m_lock = threading.Lock()

    @staticmethod
    def availablePorts() -> List[str]:
        ports = serial.tools.list_ports.comports()
        return [p.device for p in ports]

    def portName(self) -> str:
        return self.m_portName

    def setPortName(self, port: str) -> None:
        self.m_portName = port

    def baudRate(self) -> int:
        return self.m_baudRate

    def setBaudRate(self, baud: int) -> None:
        self.m_baudRate = baud

    def isConnected(self) -> bool:
        return self.m_serial is not None and self.m_serial.is_open

    def open(self) -> None:
        if self.isConnected():
            return

        if not self.m_portName:
            return

        try:
            self.m_serial = serial.Serial(
                port=self.m_portName,
                baudrate=self.m_baudRate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
                write_timeout=1.0
            )
            # Pulse DTR for GRBL controller init without holding reset
            try:
                self.m_serial.dtr = False
                self.m_serial.rts = False
                time.sleep(0.02)
                self.m_serial.dtr = True
                time.sleep(0.02)
                self.m_serial.dtr = False
            except Exception:
                pass

            self.m_running = True
            self.m_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.m_thread.start()

            self.connected.emit()
        except Exception as e:
            self.m_serial = None
            self.errorOccurred.emit(str(e))

    def close(self) -> None:
        self.m_running = False
        if self.m_thread and self.m_thread.is_alive():
            self.m_thread.join(timeout=0.5)

        with self.m_lock:
            if self.m_serial and self.m_serial.is_open:
                try:
                    self.m_serial.close()
                except Exception:
                    pass
            self.m_serial = None

        self.disconnected.emit()

    def send(self, data: Union[str, bytes]) -> None:
        with self.m_lock:
            if not self.isConnected() or self.m_serial is None:
                return

            try:
                if isinstance(data, str):
                    if len(data) == 1 and ord(data) in (
                        0x18, 0x84, 0x85, 0x90, 0x91, 0x92, 0x93, 0x94,
                        0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C,
                        0x9D, 0x9E, ord('?'), ord('!'), ord('~')
                    ):
                        self.m_serial.write(data.encode('latin1'))
                    else:
                        payload = (data.rstrip('\r\n') + "\r\n").encode('latin1')
                        self.m_serial.write(payload)
                else:
                    self.m_serial.write(data)
                self.m_serial.flush()
            except Exception as e:
                self.errorOccurred.emit(str(e))

    def _read_loop(self) -> None:
        buffer = bytearray()
        while self.m_running:
            try:
                if self.m_serial and self.m_serial.is_open:
                    available = self.m_serial.in_waiting
                    if available > 0:
                        raw = self.m_serial.read(available)
                        buffer.extend(raw)

                        while b'\n' in buffer or b'\r' in buffer:
                            # Split on newline or carriage return
                            nl_pos = buffer.find(b'\n')
                            cr_pos = buffer.find(b'\r')
                            if nl_pos == -1:
                                split_pos = cr_pos
                            elif cr_pos == -1:
                                split_pos = nl_pos
                            else:
                                split_pos = min(nl_pos, cr_pos)

                            line_bytes = buffer[:split_pos]
                            buffer = buffer[split_pos + 1:]

                            line_str = line_bytes.decode('latin1', errors='replace').strip()
                            if line_str:
                                self.dataReceived.emit(line_str)
                    else:
                        time.sleep(0.005)
                else:
                    break
            except Exception as e:
                if self.m_running:
                    self.errorOccurred.emit(str(e))
                break

        if self.m_running:
            self.m_running = False
            self.disconnected.emit()

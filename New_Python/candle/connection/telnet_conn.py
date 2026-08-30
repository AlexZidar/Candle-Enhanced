"""Telnet / TCP socket connection driver for GRBL network controllers."""

import socket
import threading
import time
from typing import Union, Optional
from .base import Connection


class TelnetConnection(Connection):
    def __init__(self, address: str = "192.168.1.100", port: int = 23, parent=None):
        super().__init__(parent)
        self.m_address: str = address
        self.m_port: int = port
        self.m_socket: Optional[socket.socket] = None
        self.m_running: bool = False
        self.m_thread: Optional[threading.Thread] = None
        self.m_lock = threading.Lock()

    def address(self) -> str:
        return self.m_address

    def setAddress(self, addr: str) -> None:
        self.m_address = addr

    def port(self) -> int:
        return self.m_port

    def setPort(self, port: int) -> None:
        self.m_port = port

    def isConnected(self) -> bool:
        return self.m_socket is not None and self.m_running

    def open(self) -> None:
        if self.isConnected():
            return

        try:
            self.m_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.m_socket.settimeout(3.0)
            self.m_socket.connect((self.m_address, self.m_port))
            self.m_socket.settimeout(0.1)

            self.m_running = True
            self.m_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.m_thread.start()

            self.connected.emit()
        except Exception as e:
            self.m_socket = None
            self.errorOccurred.emit(str(e))

    def close(self) -> None:
        self.m_running = False
        if self.m_thread and self.m_thread.is_alive():
            self.m_thread.join(timeout=0.5)

        with self.m_lock:
            if self.m_socket:
                try:
                    self.m_socket.close()
                except Exception:
                    pass
                self.m_socket = None

        self.disconnected.emit()

    def send(self, data: Union[str, bytes]) -> None:
        with self.m_lock:
            if not self.isConnected() or self.m_socket is None:
                return

            try:
                if isinstance(data, str):
                    payload = (data + "\n").encode('latin1')
                else:
                    payload = data
                self.m_socket.sendall(payload)
            except Exception as e:
                self.errorOccurred.emit(str(e))

    def _read_loop(self) -> None:
        buffer = bytearray()
        while self.m_running:
            try:
                if self.m_socket:
                    try:
                        chunk = self.m_socket.recv(4096)
                        if not chunk:
                            break
                        buffer.extend(chunk)

                        while b'\n' in buffer or b'\r' in buffer:
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
                    except socket.timeout:
                        pass
                else:
                    break
            except Exception as e:
                if self.m_running:
                    self.errorOccurred.emit(str(e))
                break

        if self.m_running:
            self.m_running = False
            self.disconnected.emit()

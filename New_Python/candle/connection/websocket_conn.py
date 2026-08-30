"""WebSocket connection driver for GRBL network controllers."""

from typing import Union
from PyQt6.QtCore import QUrl
from PyQt6.QtWebSockets import QWebSocket
from .base import Connection


class WebSocketConnection(Connection):
    def __init__(self, url: str = "ws://192.168.1.100:81", binary_mode: bool = False, parent=None):
        super().__init__(parent)
        self.m_url: str = url
        self.m_binaryMode: bool = binary_mode
        self.m_ws = QWebSocket(parent=self)

        self.m_ws.connected.connect(self.connected)
        self.m_ws.disconnected.connect(self.disconnected)
        self.m_ws.textMessageReceived.connect(self._on_text_message)
        self.m_ws.binaryMessageReceived.connect(self._on_binary_message)
        self.m_ws.errorOccurred.connect(lambda err: self.errorOccurred.emit(str(self.m_ws.errorString())))

        self.m_buffer: str = ""

    def url(self) -> str:
        return self.m_url

    def setUrl(self, url: str) -> None:
        self.m_url = url

    def binaryMode(self) -> bool:
        return self.m_binaryMode

    def setBinaryMode(self, val: bool) -> None:
        self.m_binaryMode = val

    def isConnected(self) -> bool:
        return self.m_ws.isValid()

    def open(self) -> None:
        if self.m_ws.isValid():
            self.m_ws.close()
        self.m_ws.open(QUrl(self.m_url))

    def close(self) -> None:
        if self.m_ws.isValid():
            self.m_ws.close()

    def send(self, data: Union[str, bytes]) -> None:
        if not self.m_ws.isValid():
            return

        if isinstance(data, str):
            if self.m_binaryMode:
                self.m_ws.sendBinaryMessage((data + "\n").encode('latin1'))
            else:
                self.m_ws.sendTextMessage(data + "\n")
        else:
            self.m_ws.sendBinaryMessage(data)

    def _on_text_message(self, message: str) -> None:
        if not self.m_binaryMode:
            self._process_message(message)

    def _on_binary_message(self, message: bytes) -> None:
        if self.m_binaryMode:
            self._process_message(message.decode('latin1', errors='replace'))

    def _process_message(self, message: str, delimiter: str = "\n") -> None:
        self.m_buffer += message
        while delimiter in self.m_buffer:
            pos = self.m_buffer.find(delimiter)
            line = self.m_buffer[:pos].strip()
            self.m_buffer = self.m_buffer[pos + len(delimiter):]
            if line:
                self.dataReceived.emit(line)

"""Abstract Connection Base Class for GRBL Communication."""

from typing import Union
from PyQt6.QtCore import QObject, pyqtSignal


class Connection(QObject):
    dataReceived = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def open(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def isConnected(self) -> bool:
        raise NotImplementedError

    def send(self, data: Union[str, bytes]) -> None:
        raise NotImplementedError

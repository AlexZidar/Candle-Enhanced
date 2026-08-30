"""Hardware connection drivers for Candle (Serial, Telnet, WebSocket)."""

from .base import Connection
from .serial_conn import SerialPortConnection
from .telnet_conn import TelnetConnection
from .websocket_conn import WebSocketConnection

__all__ = [
    "Connection",
    "SerialPortConnection",
    "TelnetConnection",
    "WebSocketConnection",
]

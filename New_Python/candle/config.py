"""Application configuration, constants, and enumerations for Candle."""

from enum import Enum, IntEnum
from typing import Dict, Tuple

APP_NAME = "Candle"
APP_VERSION = "2.0.0"
BUILD_NUMBER = "1"

# Serial buffer length in GRBL (127 bytes standard)
BUFFER_LENGTH = 127
PROGRESS_MIN_LINES = 10000
PROGRESS_STEP = 1000
RECENT_FILES_COUNT = 10


class ConnectionType(IntEnum):
    Serial = 0
    Telnet = 1
    WebSocket = 2


class SenderState(IntEnum):
    Unknown = -1
    Transferring = 0
    Pausing = 1
    Paused = 2
    Stopping = 3
    Stopped = 4
    ChangingTool = 5


class DeviceState(IntEnum):
    Unknown = -1
    Idle = 1
    Alarm = 2
    Run = 3
    Home = 4
    Hold0 = 5
    Hold1 = 6
    Queue = 7
    Check = 8
    Door0 = 9
    Door1 = 10
    Door2 = 11
    Door3 = 12
    Jog = 13
    Sleep = 14


DEVICE_STATUS_STRINGS: Dict[str, DeviceState] = {
    "Unknown": DeviceState.Unknown,
    "Idle": DeviceState.Idle,
    "Alarm": DeviceState.Alarm,
    "Run": DeviceState.Run,
    "Home": DeviceState.Home,
    "Hold:0": DeviceState.Hold0,
    "Hold:1": DeviceState.Hold1,
    "Queue": DeviceState.Queue,
    "Check": DeviceState.Check,
    "Door:0": DeviceState.Door0,
    "Door:1": DeviceState.Door1,
    "Door:2": DeviceState.Door2,
    "Door:3": DeviceState.Door3,
    "Jog": DeviceState.Jog,
    "Sleep": DeviceState.Sleep,
}

STATUS_CAPTIONS: Dict[DeviceState, str] = {
    DeviceState.Unknown: "Unknown",
    DeviceState.Idle: "Idle",
    DeviceState.Alarm: "Alarm",
    DeviceState.Run: "Run",
    DeviceState.Home: "Home",
    DeviceState.Hold0: "Hold (0)",
    DeviceState.Hold1: "Hold (1)",
    DeviceState.Queue: "Queue",
    DeviceState.Check: "Check",
    DeviceState.Door0: "Door (0)",
    DeviceState.Door1: "Door (1)",
    DeviceState.Door2: "Door (2)",
    DeviceState.Door3: "Door (3)",
    DeviceState.Jog: "Jog",
    DeviceState.Sleep: "Sleep",
}

STATUS_BACK_COLORS: Dict[DeviceState, str] = {
    DeviceState.Unknown: "red",
    DeviceState.Idle: "palette(button)",
    DeviceState.Alarm: "red",
    DeviceState.Run: "#00E600",
    DeviceState.Home: "#00E600",
    DeviceState.Hold0: "#E6E600",
    DeviceState.Hold1: "#E6E600",
    DeviceState.Queue: "#E6E600",
    DeviceState.Check: "palette(button)",
    DeviceState.Door0: "red",
    DeviceState.Door1: "red",
    DeviceState.Door2: "red",
    DeviceState.Door3: "red",
    DeviceState.Jog: "#00E600",
    DeviceState.Sleep: "#3366FF",
}

STATUS_FORE_COLORS: Dict[DeviceState, str] = {
    DeviceState.Unknown: "white",
    DeviceState.Idle: "palette(text)",
    DeviceState.Alarm: "white",
    DeviceState.Run: "black",
    DeviceState.Home: "black",
    DeviceState.Hold0: "black",
    DeviceState.Hold1: "black",
    DeviceState.Queue: "black",
    DeviceState.Check: "palette(text)",
    DeviceState.Door0: "white",
    DeviceState.Door1: "white",
    DeviceState.Door2: "white",
    DeviceState.Door3: "white",
    DeviceState.Jog: "black",
    DeviceState.Sleep: "white",
}


class SendCommandResult(IntEnum):
    SendDone = 0
    SendEmpty = 1
    SendQueue = 2


class VertexDataType(IntEnum):
    Line = 0
    Dash = 1
    DashDot = 2
    Point = 3
    Triangle = 4


class Planes(IntEnum):
    XY = 0
    ZX = 1
    YZ = 2


class SplineType(IntEnum):
    CubicSpline = 0      # G5
    QuadraticSpline = 1  # G5.1


class RotationAxis(IntEnum):
    RotationAxisA = 0
    RotationAxisB = 1
    RotationAxisC = 2


class GrayscaleCode(IntEnum):
    S = 0
    Z = 1


class DrawMode(IntEnum):
    Vectors = 0
    Raster = 1


class GCodeItemState(IntEnum):
    InQueue = 0
    Sent = 1
    Processed = 2
    Skipped = 3


DEFAULT_SETTINGS = {
    "Connection/type": int(ConnectionType.Serial),
    "Connection/port": "",
    "Connection/baud": 115200,
    "Connection/telnetAddress": "192.168.1.100",
    "Connection/telnetPort": 23,
    "Connection/webSocketUrl": "ws://192.168.1.100:81",
    "Connection/webSocketBinary": False,
    "Connection/resetOnConnection": True,
    "Visualizer/antialiasing": True,
    "Visualizer/msaa": False,
    "Visualizer/vsync": False,
    "Visualizer/fps": 60,
    "Visualizer/zBuffer": True,
    "Visualizer/lineWidth": 1.0,
    "Visualizer/pointSize": 4.0,
    "Visualizer/arcLength": 0.3,
    "Visualizer/arcDegree": 5.0,
    "Visualizer/arcDegreeMode": False,
    "Visualizer/simplify": False,
    "Visualizer/simplifyPrecision": 0.05,
    "Visualizer/perspective": False,
    "Visualizer/toolType": 0,  # 0=cylinder, 1=cone
    "Visualizer/toolDiameter": 3.175,
    "Visualizer/toolLength": 20.0,
    "Visualizer/toolAngle": 30.0,
    "Visualizer/colorBackground": "#1e1e1e",
    "Visualizer/colorText": "#ffffff",
    "Visualizer/colorNormal": "#4d90fe",
    "Visualizer/colorHighlight": "#ffff00",
    "Visualizer/colorZMovement": "#ff3333",
    "Visualizer/colorDrawn": "#888888",
    "Visualizer/colorStart": "#00ff00",
    "Visualizer/colorEnd": "#ff0000",
    "Visualizer/colorGridPrimary": "#404040",
    "Visualizer/colorGridSecondary": "#2a2a2a",
    "Control/safeZ": 5.0,
    "Control/safeTravel": True,
    "Control/safeTravelClearance": 3.0,
    "Control/touchPlateThickness": 15.0,
    "Control/probeMaxDistance": 30.0,
    "Control/probeSearchFeed": 40.0,
    "Control/probeLatchFeed": 10.0,
    "Control/probeRetractHeight": 5.0,
    "Control/rapidSpeed": 1000,
    "Control/acceleration": 400,
    "Control/queryStateTime": 200,
    "Control/jogSteps": ["0.01", "0.1", "1", "5", "10", "100"],
    "Control/jogStep": 3,
    "Control/jogFeeds": ["10", "50", "100", "500", "1000", "2000"],
    "Control/jogFeed": 4,
    "Control/spindleSpeedMin": 0,
    "Control/spindleSpeedMax": 10000,
    "Control/laserPowerMin": 0,
    "Control/laserPowerMax": 1000,
    "Control/toolChangeUseCommands": False,
    "Control/toolChangePause": True,
    "Control/toolChangeCommands": "G91 G0 Z20\nG90",
    "Control/toolChangeConfirm": True,
    "Control/useStartCommands": False,
    "Control/startCommands": "",
    "Control/useEndCommands": False,
    "Control/endCommands": "M5\nG91 G0 Z20\nG90",
    "Control/units": 0,  # 0=metric (mm), 1=inches
    "Control/homingEnabled": True,
    "Control/softLimitsEnabled": False,
    "Control/axisAEnabled": False,
    "Control/axisAX": True,
    "Control/machineBoundsX": 300.0,
    "Control/machineBoundsY": 180.0,
    "Control/machineBoundsZ": 45.0,
    "Parser/removeAllWhitespace": True,
    "Parser/speedOverride": -1,
    "Parser/truncateDecimalLength": 40,
    "Parser/convertArcsToLines": False,
    "Parser/smallArcThreshold": 1.0,
    "Parser/smallArcSegmentLength": 0.3,
    "UI/fontSize": 9,
    "UI/theme": 0,  # 0=Fusion Dark, 1=Fusion Light
    "UI/showProgramCommands": False,
    "UI/showUICommands": False,
    "UI/autoCompletion": True,
    "UI/autoScroll": True,
}

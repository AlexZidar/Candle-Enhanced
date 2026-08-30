"""Block-code Macro Data Model and MacroManager for custom command chaining."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import json
import uuid


class BlockType(str, Enum):
    HOME = "home"
    UNLOCK = "unlock"
    SAFE_Z = "safe_z"
    MOVE_TO = "move_to"
    MOVE_RELATIVE = "move_relative"
    ZERO_AXIS = "zero_axis"
    PROBE_Z = "probe_z"
    SPINDLE = "spindle"
    COOLANT = "coolant"
    DWELL = "dwell"
    PROMPT = "prompt"
    CUSTOM_GCODE = "custom_gcode"
    RUN_FILE = "run_file"


@dataclass
class MacroBlock:
    block_type: BlockType
    params: Dict[str, Any] = field(default_factory=dict)

    def description(self) -> str:
        bt = self.block_type
        if bt == BlockType.HOME:
            return "🏠 Home Machine ($H)"
        elif bt == BlockType.UNLOCK:
            return "🔓 Unlock Controller ($X)"
        elif bt == BlockType.SAFE_Z:
            c = self.params.get("clearance", 3.0)
            return f"⬆ Retract to Safe Top Z (G53 Z-{c:.1f}mm)"
        elif bt == BlockType.MOVE_TO:
            x = self.params.get("x", 0.0)
            y = self.params.get("y", 0.0)
            z = self.params.get("z", None)
            f = self.params.get("feed", 1000)
            coord = self.params.get("coords", "work")
            z_str = f", Z={z:.3f}" if z is not None else ""
            prefix = "G53 " if coord == "machine" else ""
            return f"📍 Move to {prefix}X={x:.3f}, Y={y:.3f}{z_str} (F{f})"
        elif bt == BlockType.MOVE_RELATIVE:
            dx = self.params.get("dx", 0.0)
            dy = self.params.get("dy", 0.0)
            dz = self.params.get("dz", 0.0)
            f = self.params.get("feed", 500)
            return f"↗ Relative Move ΔX={dx:+.1f}, ΔY={dy:+.1f}, ΔZ={dz:+.1f} (F{f})"
        elif bt == BlockType.ZERO_AXIS:
            axes = self.params.get("axes", ["X", "Y", "Z"])
            return f"🎯 Zero Work Axes ({' '.join(axes)})"
        elif bt == BlockType.PROBE_Z:
            t = self.params.get("thickness", 15.0)
            d = self.params.get("distance", 30.0)
            return f"🔍 Touch Probe & Zero Z (Plate: {t:.1f}mm, Max: {d:.0f}mm)"
        elif bt == BlockType.SPINDLE:
            state = self.params.get("state", "CW")
            rpm = self.params.get("rpm", 8000)
            delay = self.params.get("delay", 2.0)
            if state == "STOP":
                return "⏹ Spindle Stop (M5)"
            return f"⚡ Spindle {state} {rpm} RPM (Wait {delay:.1f}s)"
        elif bt == BlockType.COOLANT:
            state = self.params.get("state", "FLOOD")
            return f"💧 Coolant {state}"
        elif bt == BlockType.DWELL:
            s = self.params.get("seconds", 2.0)
            return f"⏱ Pause / Dwell ({s:.1f} sec)"
        elif bt == BlockType.PROMPT:
            msg = self.params.get("message", "Ready to proceed?")
            return f"💬 Prompt User: \"{msg}\""
        elif bt == BlockType.CUSTOM_GCODE:
            code = self.params.get("code", "")
            first_line = code.split("\n")[0] if code else ""
            return f"📝 Custom G-Code: {first_line}..."
        elif bt == BlockType.RUN_FILE:
            return "▶ Begin Loaded G-Code File"
        return str(bt.value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_type": self.block_type.value,
            "params": self.params
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MacroBlock":
        b_type = BlockType(data.get("block_type", "custom_gcode"))
        params = data.get("params", {})
        return cls(block_type=b_type, params=params)


@dataclass
class Macro:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Macro"
    color: str = "#2e7d32"  # Green
    blocks: List[MacroBlock] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "blocks": [b.to_dict() for b in self.blocks]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Macro":
        m = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Macro"),
            color=data.get("color", "#2e7d32"),
            blocks=[MacroBlock.from_dict(b) for b in data.get("blocks", [])]
        )
        return m


class MacroManager:
    """Manages collection of user macros with persistence."""

    def __init__(self, storage=None):
        self.m_storage = storage
        self.m_macros: List[Macro] = []
        self.load()

    def macros(self) -> List[Macro]:
        return self.m_macros

    def set_macros(self, macros: List[Macro]) -> None:
        self.m_macros = macros
        self.save()

    def add_macro(self, macro: Macro) -> None:
        self.m_macros.append(macro)
        self.save()

    def remove_macro(self, macro_id: str) -> None:
        self.m_macros = [m for m in self.m_macros if m.id != macro_id]
        self.save()

    def get_macro(self, macro_id: str) -> Optional[Macro]:
        for m in self.m_macros:
            if m.id == macro_id:
                return m
        return None

    def load(self) -> None:
        if not self.m_storage:
            self._load_defaults()
            return

        raw = self.m_storage.get("Macros/list", None)
        if not raw:
            self._load_defaults()
            self.save()
            return

        try:
            if isinstance(raw, str):
                data = json.loads(raw)
            else:
                data = raw
            self.m_macros = [Macro.from_dict(d) for d in data]
        except Exception:
            self._load_defaults()

    def save(self) -> None:
        if not self.m_storage:
            return
        data = [m.to_dict() for m in self.m_macros]
        self.m_storage.set("Macros/list", json.dumps(data))
        self.m_storage.sync()

    def _load_defaults(self) -> None:
        # Provide great out-of-the-box chaining examples matching user workflow
        prep_and_run = Macro(
            id="default-prep-run",
            name="Auto Home ➔ Probe ➔ Run File",
            color="#2e7d32",
            blocks=[
                MacroBlock(BlockType.HOME),
                MacroBlock(BlockType.SAFE_Z, {"clearance": 3.0}),
                MacroBlock(BlockType.MOVE_TO, {"x": 0.0, "y": 0.0, "feed": 1200, "coords": "work"}),
                MacroBlock(BlockType.PROMPT, {"message": "Position touch plate under bit and attach clip. Ready to probe?"}),
                MacroBlock(BlockType.PROBE_Z, {"thickness": 15.0, "distance": 30.0, "search_feed": 40.0, "latch_feed": 10.0, "retract": 5.0}),
                MacroBlock(BlockType.SPINDLE, {"state": "CW", "rpm": 10000, "delay": 2.0}),
                MacroBlock(BlockType.RUN_FILE)
            ]
        )

        probe_zero = Macro(
            id="default-probe-z",
            name="Z-Probe Touch Plate",
            color="#1976d2",
            blocks=[
                MacroBlock(BlockType.PROMPT, {"message": "Attach probe clip and place touch plate under cutter. Proceed?"}),
                MacroBlock(BlockType.PROBE_Z, {"thickness": 15.0, "distance": 30.0, "search_feed": 40.0, "latch_feed": 10.0, "retract": 5.0})
            ]
        )

        park_machine = Macro(
            id="default-park",
            name="Safe Park & Spindle Off",
            color="#d32f2f",
            blocks=[
                MacroBlock(BlockType.SPINDLE, {"state": "STOP"}),
                MacroBlock(BlockType.SAFE_Z, {"clearance": 3.0}),
                MacroBlock(BlockType.MOVE_TO, {"x": 0.0, "y": 0.0, "feed": 1500, "coords": "machine"})
            ]
        )

        self.m_macros = [prep_and_run, probe_zero, park_machine]

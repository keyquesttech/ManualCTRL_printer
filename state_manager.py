import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MachineState:
    """Real-time snapshot of UI requests and controller reports."""

    # ── Motion requests (set by the UI) ─────────────────────
    is_spinning_y_pos: bool = False
    is_spinning_y_neg: bool = False
    is_extruding_pos: bool = False
    is_extruding_neg: bool = False
    is_moving_z_pos: bool = False
    is_moving_z_neg: bool = False

    # ── Motion parameters (loaded from config) ──────────────
    y_feedrate: float = 2700.0    # deg/min
    e_feedrate: float = 300.0     # mm/min
    z_feedrate: float = 600.0     # mm/min
    y_step: float = 1.0           # degrees per tick
    e_step: float = 0.5           # mm per tick
    z_step: float = 0.1           # mm per tick

    # ── Temperature (set by UI, sent to controller) ─────────
    hotend_target: float = 0.0
    fan_speed: int = 0             # 0-255

    # ── Reported by controller ──────────────────────────────
    hotend_temp: float = 0.0
    y_pos: float = 0.0
    z_pos: float = 0.0
    e_pos: float = 0.0

    # ── Derived / display ───────────────────────────────────
    volumetric_flow: float = 0.0   # mm³/s (live from stream engine)
    e_velocity: float = 0.0        # mm/s
    connected: bool = False
    is_logging: bool = False


class StateManager:
    def __init__(self):
        self.state = MachineState()
        self._lock = asyncio.Lock()

    async def update_motion(self, action: str, active: bool):
        async with self._lock:
            mapping = {
                "spin_y_pos": "is_spinning_y_pos",
                "spin_y_neg": "is_spinning_y_neg",
                "extrude_pos": "is_extruding_pos",
                "extrude_neg": "is_extruding_neg",
                "move_z_pos": "is_moving_z_pos",
                "move_z_neg": "is_moving_z_neg",
            }
            attr = mapping.get(action)
            if attr:
                setattr(self.state, attr, active)
                logger.info("%s = %s", attr, active)

    async def set_temperature(self, target: str, value: float):
        async with self._lock:
            if target == "hotend":
                self.state.hotend_target = value

    async def set_fan(self, speed: int):
        async with self._lock:
            self.state.fan_speed = max(0, min(255, speed))

    async def set_feedrate(self, axis: str, value: float):
        async with self._lock:
            if axis == "y":
                self.state.y_feedrate = max(10, value)
            elif axis == "e":
                self.state.e_feedrate = max(1, value)
            elif axis == "z":
                self.state.z_feedrate = max(1, value)

    async def set_step(self, axis: str, value: float):
        async with self._lock:
            if axis == "y":
                self.state.y_step = max(0.1, value)
            elif axis == "e":
                self.state.e_step = max(0.01, value)
            elif axis == "z":
                self.state.z_step = max(0.01, value)

    def parse_controller_line(self, line: str):
        """Parse temperature and position reports from the firmware."""
        if "T:" in line:
            self._parse_temps(line)
        if "Y:" in line and "Z:" in line:
            self._parse_position(line)

    def _parse_temps(self, line: str):
        try:
            for p in line.split():
                if p.startswith("T:"):
                    self.state.hotend_temp = float(p[2:])
        except (ValueError, IndexError):
            pass

    def _parse_position(self, line: str):
        try:
            for p in line.split():
                if p.startswith("Y:"):
                    self.state.y_pos = float(p[2:])
                elif p.startswith("Z:"):
                    self.state.z_pos = float(p[2:])
                elif p.startswith("E:"):
                    self.state.e_pos = float(p[2:])
        except (ValueError, IndexError):
            pass

    def snapshot(self) -> dict:
        s = self.state
        return {
            "connected": s.connected,
            "hotend_temp": s.hotend_temp,
            "hotend_target": s.hotend_target,
            "fan_speed": s.fan_speed,
            "y_pos": s.y_pos,
            "z_pos": s.z_pos,
            "e_pos": s.e_pos,
            "is_spinning_y_pos": s.is_spinning_y_pos,
            "is_spinning_y_neg": s.is_spinning_y_neg,
            "is_extruding_pos": s.is_extruding_pos,
            "is_extruding_neg": s.is_extruding_neg,
            "is_moving_z_pos": s.is_moving_z_pos,
            "is_moving_z_neg": s.is_moving_z_neg,
            "y_feedrate": s.y_feedrate,
            "e_feedrate": s.e_feedrate,
            "z_feedrate": s.z_feedrate,
            "y_step": s.y_step,
            "e_step": s.e_step,
            "z_step": s.z_step,
            "volumetric_flow": s.volumetric_flow,
            "e_velocity": s.e_velocity,
            "is_logging": s.is_logging,
        }

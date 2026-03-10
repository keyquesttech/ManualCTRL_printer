import asyncio
import logging

from serial_manager import SerialManager
from state_manager import StateManager
from kinematics import (
    AxisLimits,
    ExtruderParams,
    build_extruder_params,
    generate_move,
    parse_gear_ratio,
)

logger = logging.getLogger(__name__)


class StreamEngine:
    """Multiplexer loop: translates active UI states into a safe command stream."""

    def __init__(self, serial_mgr: SerialManager, state_mgr: StateManager):
        self.serial = serial_mgr
        self.state = state_mgr
        self.tick_hz: int = 15

        self.y_limits = AxisLimits()
        self.z_limits = AxisLimits()
        self.e_params = ExtruderParams()

        self.bed_gear_ratio: float = 4.0
        self.bed_rotation_distance: float = 90.0

        self._task: asyncio.Task | None = None
        self._running = False
        self._temp_poll_task: asyncio.Task | None = None

    def apply_config(self, cfg):
        machine = cfg.get_section("machine")
        self.y_limits = AxisLimits(
            max_velocity=float(machine.get("max_velocity", 200)),
            max_accel=float(machine.get("max_accel", 1000)),
        )
        self.z_limits = AxisLimits(
            max_velocity=float(machine.get("max_z_velocity", 10)),
            max_accel=float(machine.get("max_z_accel", 50)),
        )
        self.e_params = build_extruder_params(cfg.get_section("extruder"))

        bed = cfg.get_section("bed")
        self.bed_gear_ratio = parse_gear_ratio(str(bed.get("gear_ratio", "")))
        self.bed_rotation_distance = float(bed.get("rotation_distance", 90))

        motion = cfg.get_section("motion")
        self.tick_hz = int(motion.get("tick_hz", 15))

        s = self.state.state
        s.y_feedrate = float(motion.get("y_feedrate", 2700))
        s.e_feedrate = float(motion.get("e_feedrate", 300))
        s.z_feedrate = float(motion.get("z_feedrate", 600))
        s.y_step = float(motion.get("y_step", 1.0))
        s.e_step = float(motion.get("e_step", 0.5))
        s.z_step = float(motion.get("z_step", 0.1))

        logger.info(
            "Config applied — bed gear %.0f:1  nozzle=%.1fmm  filament=%.1fmm  "
            "max_cross=%.1fmm²  max_e_vel=%.0fmm/s  max_vol=%.1fmm³/s",
            self.bed_gear_ratio,
            self.e_params.nozzle_diameter, self.e_params.filament_diameter,
            self.e_params.max_extrude_cross_section,
            self.e_params.max_extrude_only_velocity,
            self.e_params.max_volumetric_flow,
        )

    # ── Lifecycle ───────────────────────────────────────────

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        self._temp_poll_task = asyncio.create_task(self._temp_poll_loop())

    async def stop(self):
        self._running = False
        for t in (self._task, self._temp_poll_task):
            if t:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        self._task = None
        self._temp_poll_task = None

    # ── Main loop ───────────────────────────────────────────

    async def _loop(self):
        while self._running:
            interval = 1.0 / max(1, self.tick_hz)
            try:
                await self._tick()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Stream engine tick error")
                await asyncio.sleep(1.0 / max(1, self.tick_hz))

    async def _tick(self):
        if not self.serial.connected:
            return

        s = self.state.state
        y_req = s.y_step if s.is_spinning_y_pos else (-s.y_step if s.is_spinning_y_neg else 0.0)
        e_req = s.e_step if s.is_extruding_pos else (-s.e_step if s.is_extruding_neg else 0.0)
        z_req = s.z_step if s.is_moving_z_pos else (-s.z_step if s.is_moving_z_neg else 0.0)

        if y_req == 0.0 and e_req == 0.0 and z_req == 0.0:
            s.volumetric_flow = 0.0
            s.e_velocity = 0.0
            return

        result = generate_move(
            y_request=y_req, e_request=e_req, z_request=z_req,
            y_limits=self.y_limits, z_limits=self.z_limits, e_params=self.e_params,
            y_feed_deg_min=s.y_feedrate, e_feed_mm_min=s.e_feedrate,
            z_feed_mm_min=s.z_feedrate,
        )

        s.volumetric_flow = result.volumetric_flow
        s.e_velocity = result.e_velocity

        for cmd in result.commands:
            await self.serial.send_gcode(cmd)

    # ── Temperature polling ─────────────────────────────────

    async def _temp_poll_loop(self):
        while self._running:
            try:
                if self.serial.connected:
                    await self.serial.send_gcode("M105")
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(2)

    # ── Direct commands ─────────────────────────────────────

    async def send_temperature(self, target: str, value: float):
        if not self.serial.connected:
            return
        if target == "hotend":
            await self.serial.send_gcode(f"M104 S{value:.0f}")

    async def send_fan(self, speed: int):
        if not self.serial.connected:
            return
        await self.serial.send_gcode(f"M106 S{speed}")

    async def send_home(self, cfg=None):
        """Home Z via MANUAL_STEPPER endstop probing."""
        if not self.serial.connected:
            return

        z_lift = 5.0
        z_rest = 10.0
        z_max = 155.0

        if cfg:
            homing = cfg.get_section("homing")
            z_lift = float(homing.get("z_lift_before_home", 5.0))
            z_rest = float(homing.get("z_rest_after_home", 10.0))
            z_max = float(cfg.get("machine", "z_max", 155))

        # Lift Z a bit to avoid scraping the bed
        await self.serial.send_gcode(
            f"MANUAL_STEPPER STEPPER=z SET_POSITION=0 MOVE={z_lift} SPEED=10"
        )
        # Probe downward until endstop triggers
        await self.serial.send_gcode(
            f"MANUAL_STEPPER STEPPER=z SET_POSITION={z_max} "
            f"MOVE=0 STOP_ON_ENDSTOP=1 SPEED=5"
        )
        # Declare the endstop position as Z=0
        await self.serial.send_gcode("MANUAL_STEPPER STEPPER=z SET_POSITION=0")
        # Move to rest height
        await self.serial.send_gcode(
            f"MANUAL_STEPPER STEPPER=z MOVE={z_rest} SPEED=10"
        )

    async def send_gcode_raw(self, line: str):
        if not self.serial.connected:
            return
        await self.serial.send_gcode(line)

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from serial_manager import SerialManager
from state_manager import StateManager
from kinematics import (
    AxisLimits,
    ExtruderParams,
    build_extruder_params,
    parse_gear_ratio,
    volumetric_flow,
)

logger = logging.getLogger(__name__)


class StreamEngine:
    """Velocity-mode stream engine.

    Detects changes in the UI motion flags and sends velocity / stop
    commands to the custom firmware.  Temperature and status are polled
    periodically.
    """

    def __init__(self, serial_mgr: SerialManager, state_mgr: StateManager):
        self.serial = serial_mgr
        self.state = state_mgr
        self.tick_hz: int = 15

        self.y_limits = AxisLimits()
        self.z_limits = AxisLimits()
        self.e_params = ExtruderParams()

        self.bed_gear_ratio: float = 4.0
        self.bed_rotation_distance: float = 90.0

        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._temp_poll_task: Optional[asyncio.Task] = None

        self._prev_y: int = 0
        self._prev_e: int = 0
        self._prev_z: int = 0

        self._firmware_type: str = "custom"  # "custom" | "marlin"
        self._marlin_bed_axis: str = "B"     # axis letter for bed in G1
        self._marlin_sent_relative: bool = False  # G91 sent, need G90 when idle

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

        fw = cfg.get_section("firmware") or {}
        self._firmware_type = str(fw.get("type", "custom")).strip().lower()
        if self._firmware_type not in ("marlin", "custom"):
            self._firmware_type = "custom"
        axis = str(fw.get("marlin_bed_axis", "B")).strip().upper()
        self._marlin_bed_axis = axis if axis in ("A", "B") else "B"

        s = self.state.state
        s.y_feedrate = float(motion.get("y_feedrate", 2700))
        s.e_feedrate = float(motion.get("e_feedrate", 300))
        s.z_feedrate = float(motion.get("z_feedrate", 600))
        s.y_step = float(motion.get("y_step", 1.0))
        s.e_step = float(motion.get("e_step", 0.5))
        s.z_step = float(motion.get("z_step", 0.1))

        logger.info(
            "Config applied — bed gear %.0f:1  nozzle=%.1fmm  filament=%.1fmm  "
            "max_e_vel=%.0fmm/s  max_vol=%.1fmm³/s",
            self.bed_gear_ratio,
            self.e_params.nozzle_diameter, self.e_params.filament_diameter,
            self.e_params.max_extrude_only_velocity,
            self.e_params.max_volumetric_flow,
        )

    # ── Lifecycle ───────────────────────────────────────────

    async def start(self):
        self._running = True
        self._prev_y = self._prev_e = self._prev_z = 0
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
                await asyncio.sleep(0.25)

    async def _tick(self):
        if not self.serial.connected:
            return

        s = self.state.state

        y_dir = 1 if s.is_spinning_y_pos else (-1 if s.is_spinning_y_neg else 0)
        e_dir = 1 if s.is_extruding_pos else (-1 if s.is_extruding_neg else 0)
        z_dir = 1 if s.is_moving_z_pos  else (-1 if s.is_moving_z_neg  else 0)

        if self._firmware_type == "marlin":
            await self._tick_marlin(s, y_dir, e_dir, z_dir)
        else:
            await self._tick_custom(s, y_dir, e_dir, z_dir)

        if e_dir != 0:
            e_vel = min(abs(s.e_feedrate / 60.0), self.e_params.max_extrude_only_velocity)
            s.volumetric_flow = volumetric_flow(e_vel, self.e_params)
            s.e_velocity = e_vel
        else:
            s.volumetric_flow = 0.0
            s.e_velocity = 0.0

    async def _tick_custom(self, s, y_dir: int, e_dir: int, z_dir: int):
        if y_dir != self._prev_y:
            if y_dir != 0:
                speed = y_dir * min(abs(s.y_feedrate / 60.0), self.y_limits.max_velocity)
                await self.serial.send_gcode(f"MOV B{speed:.2f}")
            else:
                await self.serial.send_gcode("STOP B")
            self._prev_y = y_dir

        if e_dir != self._prev_e:
            if e_dir != 0:
                speed = e_dir * min(abs(s.e_feedrate / 60.0), self.e_params.max_extrude_only_velocity)
                await self.serial.send_gcode(f"MOV E{speed:.2f}")
            else:
                await self.serial.send_gcode("STOP E")
            self._prev_e = e_dir

        if z_dir != self._prev_z:
            if z_dir != 0:
                speed = z_dir * min(abs(s.z_feedrate / 60.0), self.z_limits.max_velocity)
                await self.serial.send_gcode(f"MOV Z{speed:.2f}")
            else:
                await self.serial.send_gcode("STOP Z")
            self._prev_z = z_dir

    async def _tick_marlin(self, s, y_dir: int, e_dir: int, z_dir: int):
        any_motion = y_dir != 0 or e_dir != 0 or z_dir != 0
        if any_motion and not self._marlin_sent_relative:
            await self.serial.send_gcode("G91")
            self._marlin_sent_relative = True
        if not any_motion and self._marlin_sent_relative:
            await self.serial.send_gcode("G90")
            self._marlin_sent_relative = False

        dt = 1.0 / max(1, self.tick_hz)
        y_vel = min(s.y_feedrate / 60.0, self.y_limits.max_velocity)
        z_vel = min(s.z_feedrate / 60.0, self.z_limits.max_velocity)
        e_vel = min(s.e_feedrate / 60.0, self.e_params.max_extrude_only_velocity)

        step_b = y_dir * y_vel * dt
        step_z = z_dir * z_vel * dt
        step_e = e_dir * e_vel * dt

        if y_dir != 0:
            await self.serial.send_gcode(f"G1 {self._marlin_bed_axis}{step_b:.4f} F{max(1, s.y_feedrate):.0f}")
        if z_dir != 0:
            await self.serial.send_gcode(f"G1 Z{step_z:.4f} F{max(1, s.z_feedrate):.0f}")
        if e_dir != 0:
            await self.serial.send_gcode(f"G1 E{step_e:.4f} F{max(1, s.e_feedrate):.0f}")

        self._prev_y, self._prev_e, self._prev_z = y_dir, e_dir, z_dir

    # ── Temperature polling ─────────────────────────────────

    async def _temp_poll_loop(self):
        while self._running:
            try:
                if self.serial.connected:
                    if self._firmware_type == "marlin":
                        await self.serial.send_gcode("M105")
                    else:
                        await self.serial.send_gcode("STATUS")
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
            if self._firmware_type == "marlin":
                await self.serial.send_gcode(f"M104 S{value:.0f}")
            else:
                await self.serial.send_gcode(f"TEMP {value:.0f}")

    async def send_fan(self, speed: int):
        if not self.serial.connected:
            return
        if self._firmware_type == "marlin":
            if speed <= 0:
                await self.serial.send_gcode("M107")
            else:
                await self.serial.send_gcode(f"M106 S{max(0, min(255, speed))}")
        else:
            await self.serial.send_gcode(f"FAN {speed}")

    async def send_home(self, cfg=None):
        if not self.serial.connected:
            return
        if self._firmware_type == "marlin":
            await self.serial.send_gcode("G28 Z")
        else:
            await self.serial.send_gcode("HOME")

    async def send_gcode_raw(self, line: str):
        if not self.serial.connected:
            return
        await self.serial.send_gcode(line)

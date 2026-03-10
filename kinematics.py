"""
Extrusion math and feed-rate safety for the manual-control host.

The firmware handles all stepping, pin driving, and PID.  This module
only calculates what our command generator needs:
  - Extrusion cross-section limiting
  - Volumetric flow rate
  - Velocity clamping per axis
  - MANUAL_STEPPER + G1 E command generation
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Gear Ratio ──────────────────────────────────────────────

def parse_gear_ratio(ratio_str: str) -> float:
    """Parse '80:20' → 4.0 (driven / driver)."""
    if not ratio_str:
        return 1.0
    try:
        parts = ratio_str.split(":")
        driven, driver = float(parts[0]), float(parts[1])
        return driven / driver if driver else 1.0
    except (IndexError, ValueError):
        return 1.0


# ── Axis Limits ─────────────────────────────────────────────

@dataclass
class AxisLimits:
    max_velocity: float = 200.0   # units/s (mm/s or deg/s)
    max_accel: float = 1000.0


# ── Extruder Params ─────────────────────────────────────────

@dataclass
class ExtruderParams:
    nozzle_diameter: float = 1.8
    filament_diameter: float = 1.8
    filament_cross_section: float = 0.0   # mm² — derived
    max_extrude_cross_section: float = 15.0
    max_extrude_only_velocity: float = 120
    max_extrude_only_distance: float = 100
    max_volumetric_flow: float = 0.0      # mm³/s — derived


def build_extruder_params(section: dict) -> ExtruderParams:
    nozzle_d = float(section.get("nozzle_diameter", 0.4))
    fil_d = float(section.get("filament_diameter", 1.75))

    fil_area = math.pi * (fil_d / 2.0) ** 2
    nozzle_area = math.pi * (nozzle_d / 2.0) ** 2
    max_cross = float(section.get("max_extrude_cross_section", 4.0 * nozzle_area))
    max_vel = float(section.get("max_extrude_only_velocity", 120))
    max_dist = float(section.get("max_extrude_only_distance", 100))

    return ExtruderParams(
        nozzle_diameter=nozzle_d,
        filament_diameter=fil_d,
        filament_cross_section=fil_area,
        max_extrude_cross_section=max_cross,
        max_extrude_only_velocity=max_vel,
        max_extrude_only_distance=max_dist,
        max_volumetric_flow=fil_area * max_vel,
    )


# ── Checks ──────────────────────────────────────────────────

def check_cross_section(e_distance: float, xy_distance: float,
                        params: ExtruderParams) -> bool:
    if xy_distance <= 0:
        return True
    cross = params.filament_cross_section * abs(e_distance) / xy_distance
    return cross <= params.max_extrude_cross_section


def volumetric_flow(e_velocity_mm_s: float, params: ExtruderParams) -> float:
    return abs(e_velocity_mm_s) * params.filament_cross_section


# ── Feed-Rate Helpers ───────────────────────────────────────

def clamp_velocity(requested_units_s: float, limit_units_s: float) -> float:
    return min(abs(requested_units_s), abs(limit_units_s))


# ── Move Generation ─────────────────────────────────────────

@dataclass
class MoveResult:
    commands: list[str] = field(default_factory=list)
    y_deg: float = 0.0
    e_mm: float = 0.0
    z_mm: float = 0.0
    e_velocity: float = 0.0        # mm/s — effective extrusion speed
    volumetric_flow: float = 0.0   # mm³/s
    clamped: bool = False


def generate_move(
    y_request: float,
    e_request: float,
    z_request: float,
    y_limits: AxisLimits,
    z_limits: AxisLimits,
    e_params: ExtruderParams,
    y_feed_deg_min: float,
    e_feed_mm_min: float,
    z_feed_mm_min: float,
) -> MoveResult:
    cmds: list[str] = []
    clamped = False

    # Cross-section check when bed is rotating and extruding simultaneously
    if y_request != 0 and e_request != 0:
        if not check_cross_section(e_request, abs(y_request), e_params):
            max_e = (e_params.max_extrude_cross_section * abs(y_request)
                     / e_params.filament_cross_section)
            e_request = math.copysign(max_e, e_request)
            clamped = True

    # Clamp extrude-only velocity
    e_vel_s = abs(e_feed_mm_min) / 60.0
    if e_request != 0:
        if e_vel_s > e_params.max_extrude_only_velocity:
            e_vel_s = e_params.max_extrude_only_velocity
            e_feed_mm_min = math.copysign(e_vel_s * 60.0, e_feed_mm_min)
            clamped = True

    # Bed rotation → MANUAL_STEPPER
    if y_request != 0:
        y_speed = clamp_velocity(abs(y_feed_deg_min) / 60.0, y_limits.max_velocity)
        cmds.append(
            f"MANUAL_STEPPER STEPPER=bed SET_POSITION=0 "
            f"MOVE={y_request:.4f} SPEED={y_speed:.2f}"
        )

    # Z axis → MANUAL_STEPPER
    if z_request != 0:
        z_speed = clamp_velocity(abs(z_feed_mm_min) / 60.0, z_limits.max_velocity)
        cmds.append(
            f"MANUAL_STEPPER STEPPER=z SET_POSITION=0 "
            f"MOVE={z_request:.4f} SPEED={z_speed:.2f}"
        )

    # Extruder → standard G-code (works with kinematics: none)
    if e_request != 0:
        e_feed_clamped = clamp_velocity(e_vel_s, e_params.max_extrude_only_velocity) * 60.0
        cmds.append("M83")
        cmds.append(f"G1 E{e_request:.4f} F{e_feed_clamped:.0f}")

    # Flow tracking
    effective_e_vel = clamp_velocity(e_vel_s, e_params.max_extrude_only_velocity) if e_request else 0.0
    vol = volumetric_flow(effective_e_vel, e_params)

    return MoveResult(
        commands=cmds,
        y_deg=y_request,
        e_mm=e_request,
        z_mm=z_request,
        e_velocity=effective_e_vel,
        volumetric_flow=vol,
        clamped=clamped,
    )

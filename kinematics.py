"""
Extrusion math and parameter structures for the manual-control host.

The custom firmware handles all stepping, pin driving, and PID.  This module
provides:
  - Extruder parameter calculation (cross-section, volumetric flow limits)
  - Gear ratio parsing
  - Volumetric flow rate computation for the UI
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ── Gear Ratio ──────────────────────────────────────────────

def parse_gear_ratio(ratio_str: str) -> float:
    """Parse '80:20' -> 4.0 (driven / driver)."""
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
    filament_cross_section: float = 0.0
    max_extrude_cross_section: float = 15.0
    max_extrude_only_velocity: float = 120
    max_extrude_only_distance: float = 100
    max_volumetric_flow: float = 0.0


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


# ── Flow helpers ────────────────────────────────────────────

def volumetric_flow(e_velocity_mm_s: float, params: ExtruderParams) -> float:
    return abs(e_velocity_mm_s) * params.filament_cross_section

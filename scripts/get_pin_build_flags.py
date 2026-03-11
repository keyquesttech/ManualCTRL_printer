#!/usr/bin/env python3
"""
Read printer config and output -D flags for custom firmware build (pins and directions).
Usage: run from repo root; prints space-separated flags to stdout.
"""
from __future__ import annotations

import os
import sys

# Run from repo root so config_manager and printer.cfg are found
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from config_manager import ConfigManager

# Config key (pins section) -> C macro name
PIN_MACROS = {
    "bed_step": "BED_STEP_PIN",
    "bed_dir": "BED_DIR_PIN",
    "bed_enable": "BED_ENABLE_PIN",
    "bed_dir_invert": "BED_DIR_INVERT",
    "z_step": "Z_STEP_PIN",
    "z_dir": "Z_DIR_PIN",
    "z_enable": "Z_ENABLE_PIN",
    "z_dir_invert": "Z_DIR_INVERT",
    "e_step": "E_STEP_PIN",
    "e_dir": "E_DIR_PIN",
    "e_enable": "E_ENABLE_PIN",
    "e_dir_invert": "E_DIR_INVERT",
    "tmc_rx": "TMC_RX_PIN",
    "tmc_tx": "TMC_TX_PIN",
    "tmc_bed_addr": "TMC_BED_ADDR",
    "tmc_z_addr": "TMC_Z_ADDR",
    "tmc_e_addr": "TMC_E_ADDR",
    "heater": "HOTEND_HEATER_PIN",
    "thermistor": "HOTEND_THERM_PIN",
    "fan_part": "FAN_PART_PIN",
    "fan_hotend": "FAN_HOTEND_PIN",
    "z_endstop": "Z_ENDSTOP_PIN",
    "beeper": "BEEPER_PIN",
}


def _to_flag_value(val) -> str:
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(int(val))
    s = str(val).strip()
    return s if s else None


def main() -> None:
    os.chdir(REPO_ROOT)
    cfg = ConfigManager()
    section = cfg.get_section("pins") or {}
    out = []
    for key, macro in PIN_MACROS.items():
        if key not in section:
            continue
        val = _to_flag_value(section[key])
        if val is None:
            continue
        # Avoid spaces in value so shell doesn't break
        out.append(f"-D{macro}={val}")
    print(" ".join(out))


if __name__ == "__main__":
    main()

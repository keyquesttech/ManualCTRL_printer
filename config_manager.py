from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DEFAULT_CONFIG_PATH = BASE_DIR / "default_config.yaml"
USER_CONFIG_PATH = BASE_DIR / "printer.cfg"


def _str(label, **kw):
    return {"type": "str", "label": label, **kw}

def _int(label, **kw):
    return {"type": "int", "label": label, **kw}

def _float(label, **kw):
    return {"type": "float", "label": label, **kw}

def _bool(label, **kw):
    return {"type": "bool", "label": label, **kw}

def _text(label, **kw):
    return {"type": "text", "label": label, **kw}

def _select(label, options, **kw):
    return {"type": "str", "label": label, "options": options, **kw}


SECTION_SCHEMA: dict[str, dict[str, dict[str, Any]]] = {
    "serial": {
        "port":      _str("Serial Port", help="Device path or by-id symlink"),
        "baud_rate": _select("Baud Rate", [115200, 250000, 500000]),
    },
    "machine": {
        "max_velocity":   _float("Max Velocity (mm/s)"),
        "max_accel":      _float("Max Acceleration (mm/s\u00b2)"),
        "max_z_velocity": _float("Max Z Velocity (mm/s)"),
        "max_z_accel":    _float("Max Z Acceleration (mm/s\u00b2)"),
        "z_max":          _float("Z Max Travel (mm)"),
    },
    "bed": {
        "gear_ratio":        _str("Gear Ratio", help="driven:driver teeth, e.g. 80:20"),
        "rotation_distance": _float("Rotation Distance (deg/rev)", help="Degrees of bed rotation per motor revolution"),
    },
    "extruder": {
        "nozzle_diameter":           _float("Nozzle Diameter (mm)"),
        "filament_diameter":         _float("Filament Diameter (mm)"),
        "rotation_distance":         _float("Rotation Distance (mm/rev)", help="mm filament per motor revolution"),
        "max_extrude_cross_section": _float("Max Extrude Cross Section (mm\u00b2)"),
        "max_extrude_only_velocity": _float("Max Extrude-Only Velocity (mm/s)"),
        "max_extrude_only_distance": _float("Max Extrude-Only Distance (mm)"),
        "max_temp":                  _float("Max Temp (\u00b0C)", help="UI input limit for hotend target"),
    },
    "homing": {
        "z_lift_before_home": _float("Z Lift Before Home (mm)"),
        "z_rest_after_home":  _float("Z Rest After Home (mm)"),
    },
    "motion": {
        "y_feedrate": _float("Y Feedrate (deg/min)"),
        "y_step":     _float("Y Step (deg/tick)"),
        "e_feedrate": _float("E Feedrate (mm/min)"),
        "e_step":     _float("E Step (mm/tick)"),
        "z_feedrate": _float("Z Feedrate (mm/min)"),
        "z_step":     _float("Z Step (mm/tick)"),
        "tick_hz":    _int("Tick Frequency (Hz)", help="Multiplexer loop rate"),
    },
    "macros": {
        "startup_gcode":  _text("Startup G-code"),
        "shutdown_gcode": _text("Shutdown G-code"),
    },
}

SECTION_LABELS: dict[str, str] = {
    "serial":   "Serial Connection",
    "machine":  "Machine Limits",
    "bed":      "Bed Rotation (80T:20T)",
    "extruder": "Extruder (Orbiter 2.0)",
    "homing":   "Homing Sequence",
    "motion":   "Manual Control Defaults",
    "macros":   "G-code Macros",
}


class ConfigManager:
    def __init__(self, config_path: Path = USER_CONFIG_PATH):
        self.config_path = config_path
        self._data: dict = {}
        self.load()

    def load(self):
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                self._data = yaml.safe_load(f) or {}
            logger.info("Loaded config from %s", self.config_path)
        else:
            self._load_defaults()
            self.save()
            logger.info("Created default config at %s", self.config_path)

    def _load_defaults(self):
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            self._data = yaml.safe_load(f) or {}

    def save(self):
        backup = self.config_path.with_suffix(".cfg.bak")
        if self.config_path.exists():
            shutil.copy2(self.config_path, backup)
        with open(self.config_path, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        logger.info("Config saved to %s", self.config_path)

    def get_raw_yaml(self) -> str:
        return yaml.dump(self._data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def set_raw_yaml(self, text: str):
        parsed = yaml.safe_load(text)
        if not isinstance(parsed, dict):
            raise ValueError("Config must be a YAML mapping")
        self._data = parsed
        self.save()

    @property
    def data(self) -> dict:
        return self._data

    def get_section(self, section: str) -> dict:
        return self._data.get(section, {})

    def set_section(self, section: str, values: dict):
        self._data[section] = values
        self.save()

    def update_field(self, section: str, key: str, value):
        if section not in self._data:
            self._data[section] = {}
        schema = SECTION_SCHEMA.get(section, {}).get(key, {})
        self._data[section][key] = _coerce(value, schema.get("type", "str"))
        self.save()

    def reset_to_defaults(self):
        self._load_defaults()
        self.save()

    def get(self, section: str, key: str, default=None):
        return self._data.get(section, {}).get(key, default)

    def schema_for_ui(self) -> dict:
        result = {}
        for section, fields in SECTION_SCHEMA.items():
            sec_data = self._data.get(section, {})
            result[section] = {
                "label": SECTION_LABELS.get(section, section),
                "fields": {},
            }
            for key, meta in fields.items():
                result[section]["fields"][key] = {
                    **meta,
                    "value": sec_data.get(key, ""),
                }
        return result


def _coerce(value, dtype: str):
    if dtype == "int":
        return int(float(value))
    elif dtype == "float":
        return float(value)
    elif dtype == "bool":
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    elif dtype in ("str", "text"):
        return str(value)
    return value

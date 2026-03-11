"""
G-code session logger.

When active, every command sent to the printer (except temperature polling)
is written to a timestamped .gcode file inside the gcode_logs/ directory.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, IO

logger = logging.getLogger(__name__)

LOGS_DIR = Path(__file__).parent / "gcode_logs"

EXCLUDE_PREFIXES = ("M105",)


class GcodeLogger:
    def __init__(self):
        self._file: Optional[IO] = None
        self._filename: str = ""
        self.active: bool = False

    def start(self):
        LOGS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._filename = f"session_{ts}.gcode"
        path = LOGS_DIR / self._filename
        self._file = open(path, "w", encoding="utf-8")
        self._file.write(f"; ManualCTRL G-code log\n")
        self._file.write(f"; Started: {datetime.now().isoformat()}\n\n")
        self.active = True
        logger.info("G-code logging started → %s", path)

    def stop(self):
        if self._file:
            self._file.write(f"\n; Ended: {datetime.now().isoformat()}\n")
            self._file.close()
            self._file = None
        self.active = False
        self._filename = ""
        logger.info("G-code logging stopped")

    def log(self, line: str):
        if not self.active or not self._file:
            return
        stripped = line.strip()
        if not stripped:
            return
        for prefix in EXCLUDE_PREFIXES:
            if stripped.startswith(prefix):
                return
        self._file.write(stripped + "\n")
        self._file.flush()

    @property
    def current_file(self) -> str:
        return self._filename

    def list_logs(self) -> list[str]:
        LOGS_DIR.mkdir(exist_ok=True)
        return sorted(
            [f.name for f in LOGS_DIR.glob("*.gcode")],
            reverse=True,
        )

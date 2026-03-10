import asyncio
import logging
import serial
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class SerialManager:
    """Async wrapper around pyserial for G-code send/receive with buffer tracking."""

    OK_PREFIXES = (b"ok",)

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baudrate: int = 115200,
        max_pending: int = 4,
    ):
        self.port = port
        self.baudrate = baudrate
        self.max_pending = max_pending

        self._serial: Optional[serial.Serial] = None
        self._pending = 0
        self._pending_event = asyncio.Event()
        self._pending_event.set()
        self._lock = asyncio.Lock()
        self._running = False
        self._reader_task: Optional[asyncio.Task] = None
        self._on_line: Optional[Callable[[str], None]] = None
        self._on_send: Optional[Callable[[str], None]] = None

    @property
    def connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def set_line_callback(self, cb: Callable[[str], None]):
        """Register a callback invoked for every line received from the controller."""
        self._on_line = cb

    def set_send_callback(self, cb: Callable[[str], None]):
        """Register a callback invoked for every line sent to the controller."""
        self._on_send = cb

    async def connect(self):
        loop = asyncio.get_running_loop()
        try:
            self._serial = await loop.run_in_executor(
                None,
                lambda: serial.Serial(
                    self.port,
                    self.baudrate,
                    timeout=0.1,
                    write_timeout=2,
                ),
            )
            self._running = True
            self._pending = 0
            self._pending_event.set()
            self._reader_task = asyncio.create_task(self._read_loop())
            logger.info("Connected to %s @ %d", self.port, self.baudrate)
        except serial.SerialException as exc:
            logger.error("Serial connect failed: %s", exc)
            self._serial = None
            raise

    async def disconnect(self):
        self._running = False
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None
        if self._serial and self._serial.is_open:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._serial.close)
        self._serial = None
        self._pending = 0
        self._pending_event.set()
        logger.info("Disconnected")

    async def send_gcode(self, line: str):
        """Send a single G-code line, respecting the planner buffer limit."""
        if not self.connected:
            raise RuntimeError("Serial not connected")

        await self._pending_event.wait()

        async with self._lock:
            cleaned = line.strip()
            if not cleaned:
                return
            loop = asyncio.get_running_loop()
            payload = (cleaned + "\n").encode("ascii", errors="ignore")
            await loop.run_in_executor(None, self._serial.write, payload)
            self._pending += 1
            if self._pending >= self.max_pending:
                self._pending_event.clear()
            if self._on_send:
                self._on_send(cleaned)
            logger.debug("TX: %s (pending=%d)", cleaned, self._pending)

    async def _read_loop(self):
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                raw: bytes = await loop.run_in_executor(
                    None, self._serial.readline
                )
                if not raw:
                    continue
                line = raw.strip()
                if not line:
                    continue

                decoded = line.decode("ascii", errors="replace")
                logger.debug("RX: %s", decoded)

                if self._on_line:
                    self._on_line(decoded)

                if line.lower().startswith(self.OK_PREFIXES):
                    self._pending = max(0, self._pending - 1)
                    if self._pending < self.max_pending:
                        self._pending_event.set()
            except serial.SerialException:
                logger.error("Serial read error – disconnecting")
                self._running = False
                break
            except asyncio.CancelledError:
                break

    async def emergency_stop(self):
        """Send M112 emergency stop bypassing the buffer."""
        if not self.connected:
            return
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None, self._serial.write, b"M112\n"
            )
            logger.warning("Emergency stop sent")
        except serial.SerialException:
            logger.error("Failed to send emergency stop")

# ManualCTRL Printer Host

A lightweight web-based controller for a polar 3D printer running on a Raspberry Pi with a BTT SKR Mini E3 V3.0 board. Uses **custom firmware** (no Klipper/Marlin dependency) for direct hardware control with full customizability.

Provides real-time manual control via hold-to-move buttons, temperature management, a G-code console, G-code session logging, and a full configuration editor — all accessible from any browser at **http://manualctrl.local:8000**.

## Requirements

- **Raspberry Pi** (any model — tested on Pi OS Lite 32-bit Bookworm)
- **Python 3.9+** (Bookworm ships with 3.11)
- **BTT SKR Mini E3 V3.0** (STM32G0B1) connected via USB

## Quick Install (Raspberry Pi)

```bash
git clone https://github.com/keyquesttech/ManualCTRL_printer.git
cd ManualCTRL_printer
chmod +x install.sh
./install.sh
```

The installer handles everything: system packages, mDNS hostname, Python venv, firmware build (via Arduino CLI), and systemd service.

After the firmware builds, flash it to the SKR board:
1. Copy `firmware.bin` to an SD card
2. Insert into the SKR Mini E3 V3.0
3. Power cycle the board

Then open:
- **http://manualctrl.local:8000** — Control panel
- **http://manualctrl.local:8000/config** — Configuration editor

## Updating

```bash
~/ManualCTRL_printer/update.sh              # host code only
~/ManualCTRL_printer/update.sh --firmware   # also rebuild firmware
```

## Uninstalling

```bash
~/ManualCTRL_printer/uninstall.sh
```

Removes the systemd service, Arduino CLI, PlatformIO data, and the project directory.

## Custom Firmware

The `firmware/ManualCTRL/` directory contains the Arduino sketch targeting the STM32G0B1 on the SKR Mini E3 V3.0. It replaces Klipper/Marlin with a purpose-built firmware that:

- Drives 3 steppers (bed rotation, Z axis, extruder) via TMC2209 UART
- Reads a 100K NTC thermistor and runs PID for the hotend heater
- Controls part cooling and hotend fans
- Reads the Z endstop for homing
- Provides toggleable safety (thermal runaway, over-temperature)
- Speaks a simple text protocol over USB serial

The firmware builds with **Arduino CLI** on the Pi (no PlatformIO ARM issues) and also with **PlatformIO** on PC for development.

### Serial Protocol

| Command | Description |
|---------|-------------|
| `MOV B<speed>` | Rotate bed continuously (deg/s, signed) |
| `MOV Z<speed>` | Move Z continuously (mm/s, signed) |
| `MOV E<speed>` | Extrude continuously (mm/s, signed) |
| `STOP [B\|Z\|E]` | Decelerate-stop axis (or all) |
| `TEMP <°C>` | Set hotend target temperature |
| `FAN <0-255>` | Set part cooling fan speed |
| `HOME` | Home Z axis via endstop |
| `ESTOP` | Emergency stop — kill heaters + disable steppers |
| `ENABLE` | Re-enable steppers after ESTOP |
| `ZERO B\|Z\|E` | Reset axis position counter |
| `SAFETY ON\|OFF` | Toggle safety checks |
| `STATUS` | Request full status report |

## Manual / Development Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Open `http://localhost:8000` in your browser.

### Building firmware on PC (PlatformIO)

```bash
cd firmware
pio run
```

The `platformio.ini` is configured to find sources in `ManualCTRL/`.

## Configuration

All host-side settings are stored in `printer.cfg` (auto-created from `default_config.yaml` on first run). Edit via the web interface at `/config`.

| Section | What it controls |
|---------|-----------------|
| **Serial** | Port, baud rate |
| **Machine** | Velocity/accel limits, Z max travel |
| **Bed** | Gear ratio, rotation distance |
| **Extruder** | Nozzle/filament diameters, cross-section limits, max temp |
| **Motion** | Default feedrates, tick frequency |
| **Macros** | Startup / shutdown command sequences |

## Project Structure

```
main.py                  – FastAPI server, WebSocket, REST config API
serial_manager.py        – Async serial communication with buffer tracking
state_manager.py         – Machine state & controller response parsing
stream_engine.py         – Velocity-mode engine: UI states → MOV/STOP commands
kinematics.py            – Extruder params, volumetric flow calculations
config_manager.py        – YAML config load/save/validate with schema
gcode_logger.py          – Session command logging (toggle from UI)
default_config.yaml      – Factory default configuration
static/                  – Web frontend (HTML, CSS, JS)
firmware/
  ManualCTRL/            – Arduino sketch (custom STM32 firmware)
  boards/                – PlatformIO custom board definition
  platformio.ini         – PlatformIO config (for PC development)
install.sh               – One-command Raspberry Pi installer
update.sh                – One-command updater (--firmware to rebuild)
uninstall.sh             – One-command uninstaller
printer_host.service     – systemd unit file
```

## Architecture

```
Browser  ←WebSocket→  FastAPI (Pi)  ←USB Serial→  STM32 Firmware (SKR)
```

1. **Hold-to-move**: Mouse/touch events send motion start/stop over WebSocket
2. **Velocity mode**: Stream engine sends `MOV <axis><speed>` on press, `STOP` on release
3. **Buffer tracking**: Serial manager respects `ok` acknowledgments
4. **Custom firmware**: AccelStepper for motion, TMCStepper for driver config, PID for heater
5. **mDNS**: Discoverable at `manualctrl.local` via Avahi
6. **Toggleable safety**: Thermal runaway and over-temp protection, can be disabled for testing

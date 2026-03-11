# ManualCTRL Printer Host

A lightweight web-based controller for a polar 3D printer running on a Raspberry Pi with a BTT SKR Mini E3 V3.0 board. Provides real-time manual control via hold-to-move buttons, temperature management, a G-code console, G-code session logging, and a full configuration editor — all accessible from any browser at **http://manualctrl.local:8000**.

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

The installer handles everything: system packages, mDNS hostname, Python venv, Klipper firmware build, and systemd service. After install, open:

- **http://manualctrl.local:8000** — Control panel
- **http://manualctrl.local:8000/config** — Configuration editor

## Updating

Pull the latest code and restart the service with a single command:

```bash
~/ManualCTRL_printer/update.sh
```

## Manual / Development Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows
pip install -r requirements.txt

python main.py
```

Open `http://localhost:8000` in your browser.

## Configuration

All host-side settings are stored in `printer.cfg` (auto-created from `default_config.yaml` on first run). Edit via the web interface at `/config` which provides:

- **Structured Editor** — form-based fields grouped by section
- **Raw YAML Editor** — direct YAML editing for advanced users

Configuration sections:

| Section | What it controls |
|---------|-----------------|
| **Serial** | Port, baud rate |
| **Machine** | Velocity/accel limits, Z max travel |
| **Bed** | Gear ratio, rotation distance |
| **Extruder** | Nozzle/filament diameters, cross-section limits, max temp |
| **Homing** | Z lift/rest distances for the homing sequence |
| **Motion** | Default feedrates, step sizes, tick frequency |
| **Macros** | Startup / shutdown G-code sequences |

## Project Structure

```
main.py              – FastAPI server, WebSocket, REST config API
serial_manager.py    – Async serial communication with buffer tracking
state_manager.py     – Machine state & controller response parsing
stream_engine.py     – Multiplexer loop: UI states → G-code stream
kinematics.py        – Extrusion math, velocity clamping, move generation
config_manager.py    – YAML config load/save/validate with schema
gcode_logger.py      – Session G-code logging (toggle from UI)
default_config.yaml  – Factory default configuration
printer.cfg          – User configuration (auto-created, gitignored)
static/
  index.html         – SPA with Control + Config pages
  style.css          – Dark-theme responsive styles (yellow/gray palette)
  app.js             – WebSocket client, config editor, navigation
install.sh           – One-command Raspberry Pi installer with mDNS
update.sh            – One-command updater (git pull + restart service)
printer_host.service – systemd unit file
Printer_data/        – Klipper configuration files for the MCU
```

## Architecture

1. **mDNS**: The installer sets the Pi's hostname to `manualctrl` and enables Avahi, making it discoverable as `manualctrl.local`
2. **Hold-to-move**: Mouse/touch events send `state: true/false` over WebSocket — simultaneous bed rotation + extrusion supported
3. **Multiplexer loop** (configurable Hz): reads active motion states, generates MANUAL_STEPPER / G1 commands with safety clamping
4. **Buffer tracking**: only sends when the controller acknowledges with `ok`
5. **Config API**: REST endpoints at `/api/config` for reading/writing `printer.cfg`
6. **Live reload**: Save & Restart reconnects the serial port with new settings
7. **G-code logging**: Toggle recording from the UI — all sent commands are saved to timestamped `.gcode` files

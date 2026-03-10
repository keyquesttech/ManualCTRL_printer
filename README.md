# ManualCTRL Printer Host

A lightweight web-based controller for a polar 3D printer running on a Raspberry Pi with a BTT SKR Mini E3 V3.0 board. Provides real-time manual control via hold-to-move buttons, temperature management, a G-code console, and a full configuration editor — all accessible from any browser at **http://manualctrl.local:8000**.

## Quick Install (Raspberry Pi)

```bash
git clone https://github.com/YOUR_USER/ManualCTRL_printer.git
cd ManualCTRL_printer
chmod +x install.sh
./install.sh
```

The installer handles everything: system packages, mDNS hostname, Python venv, Klipper firmware build, and systemd service. After install, open:

- **http://manualctrl.local:8000** — Control panel
- **http://manualctrl.local:8000/config** — Configuration editor

## Manual / Development Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows
pip install -r requirements.txt

export SERIAL_PORT=/dev/ttyACM0
export SERIAL_BAUD=115200

python main.py
```

Open `http://localhost:8000` in your browser.

## Configuration

ManualCTRL uses a Klipper-style configuration system. All settings are stored in `printer.cfg` (auto-created from defaults on first run).

Edit via the web interface at `/config` which provides:
- **Structured Editor** — form-based editing with dropdowns for pin names, sensor types, microstep values, etc.
- **Raw YAML Editor** — direct YAML editing for advanced users

Configuration sections include:
- **System** — serial port, baud rate, hostname
- **MCU / Board** — board model, chip
- **Stepper Y** — step/dir/enable pins, microsteps, rotation distance, endstop
- **Extruder** — pins, heater, thermistor, PID tuning, pressure advance
- **Heated Bed** — pins, thermistor, PID tuning
- **Fans** — part cooling, heater fan, controller fan with pin assignments
- **Motion** — feedrates, step sizes, tick frequency
- **Macros** — startup and shutdown G-code sequences

## Project Structure

```
main.py              – FastAPI server, WebSocket, REST config API
serial_manager.py    – Async serial communication with buffer tracking
state_manager.py     – Machine state & controller response parsing
stream_engine.py     – Multiplexer loop: UI states → G-code stream
config_manager.py    – YAML config load/save/validate with schema
default_config.yaml  – Factory default configuration
printer.cfg          – User configuration (auto-created)
static/
  index.html         – SPA with Control + Config pages
  style.css          – Dark-theme responsive styles
  app.js             – WebSocket client, config editor, navigation
install.sh           – One-command Raspberry Pi installer with mDNS
printer_host.service – systemd unit file
klipper.config       – Klipper .config for SKR Mini E3 V3.0
```

## Architecture

1. **mDNS**: The installer sets the Pi's hostname to `manualctrl` and enables Avahi, making it discoverable as `manualctrl.local`
2. **Hold-to-move**: Mouse/touch events send `state: true/false` over WebSocket
3. **Multiplexer loop** (configurable Hz): reads active states, generates relative G-code
4. **Buffer tracking**: only sends when the controller acknowledges with `ok`
5. **Config API**: REST endpoints at `/api/config` for reading/writing `printer.cfg`
6. **Live reload**: Save & Restart reconnects the serial port with new settings

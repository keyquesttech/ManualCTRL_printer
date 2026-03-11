#!/usr/bin/env bash
#
# ManualCTRL Printer Host – single-command installer for Raspberry Pi
# Usage:  chmod +x install.sh && ./install.sh
#
set -euo pipefail

REPO_URL="https://github.com/keyquesttech/ManualCTRL_printer.git"
INSTALL_DIR="$HOME/ManualCTRL_printer"
HOSTNAME="manualctrl"

echo "========================================="
echo "  ManualCTRL Printer Host – Installer"
echo "========================================="

# ── 1. System packages ──────────────────────────────────────
echo "[1/7] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git \
    build-essential libffi-dev \
    gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi \
    avahi-daemon avahi-utils libnss-mdns

# ── 2. Set hostname for mDNS (manualctrl.local) ─────────────
echo "[2/7] Configuring hostname → ${HOSTNAME}.local ..."
CURRENT_HOSTNAME=$(hostname)
if [ "$CURRENT_HOSTNAME" != "$HOSTNAME" ]; then
    sudo hostnamectl set-hostname "$HOSTNAME"
    sudo sed -i "s/127\.0\.1\.1.*$/127.0.1.1\t${HOSTNAME}/" /etc/hosts
    echo "  Hostname changed from '$CURRENT_HOSTNAME' to '$HOSTNAME'"
else
    echo "  Hostname already set to '$HOSTNAME'"
fi

sudo systemctl enable avahi-daemon
sudo systemctl restart avahi-daemon
echo "  mDNS active – reachable at http://${HOSTNAME}.local:8000"

# ── 3. Clone the project ────────────────────────────────────
echo "[3/7] Cloning project repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  Directory exists – pulling latest..."
    cd "$INSTALL_DIR" && git pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ── 4. Python virtual environment ───────────────────────────
echo "[4/7] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ── 5. Build custom firmware ────────────────────────────────
echo "[5/7] Building ManualCTRL firmware for SKR Mini E3 V3.0..."
pip install platformio

ARCH=$(uname -m)
if [ "$ARCH" = "armv7l" ] || [ "$ARCH" = "armv6l" ]; then
    echo "  32-bit ARM detected — linking system ARM toolchain for PlatformIO"
    TOOL_DIR="$HOME/.platformio/packages/toolchain-gccarmnoneeabi"
    rm -rf "$TOOL_DIR"
    mkdir -p "$(dirname "$TOOL_DIR")"
    ln -sf /usr "$TOOL_DIR"
    PIO_ENV="pi"
else
    PIO_ENV="default"
fi

cd "$INSTALL_DIR/firmware"
pio run -e "$PIO_ENV"

FIRMWARE_BIN="$INSTALL_DIR/firmware/.pio/build/${PIO_ENV}/firmware.bin"
if [ -f "$FIRMWARE_BIN" ]; then
    cp "$FIRMWARE_BIN" "$INSTALL_DIR/firmware.bin"
    echo ""
    echo "  ╔═══════════════════════════════════════════════════╗"
    echo "  ║  Firmware built: ~/ManualCTRL_printer/firmware.bin║"
    echo "  ║                                                   ║"
    echo "  ║  To flash:                                        ║"
    echo "  ║    1. Copy firmware.bin to an SD card              ║"
    echo "  ║    2. Insert SD into the SKR Mini E3 V3.0         ║"
    echo "  ║    3. Power cycle the board                       ║"
    echo "  ╚═══════════════════════════════════════════════════╝"
    echo ""
else
    echo "  WARNING: Firmware build may have failed – check output above."
fi

# ── 6. Systemd service ──────────────────────────────────────
echo "[6/7] Installing systemd service..."
cd "$INSTALL_DIR"
sudo cp printer_host.service /etc/systemd/system/printer_host.service

sudo sed -i "s|User=pi|User=$USER|g" /etc/systemd/system/printer_host.service
sudo sed -i "s|/home/pi|$HOME|g" /etc/systemd/system/printer_host.service

sudo systemctl daemon-reload
sudo systemctl enable printer_host.service
sudo systemctl start printer_host.service

# ── 7. Done ──────────────────────────────────────────────────
IP_ADDR=$(hostname -I | awk '{print $1}')
echo ""
echo "[7/7] Installation complete!"
echo ""
echo "  ┌─────────────────────────────────────────────────┐"
echo "  │  ManualCTRL is now running!                     │"
echo "  │                                                 │"
echo "  │  Local:   http://${HOSTNAME}.local:8000         │"
echo "  │  Network: http://${IP_ADDR}:8000                │"
echo "  │  Config:  http://${HOSTNAME}.local:8000/config  │"
echo "  │                                                 │"
echo "  │  Service: sudo systemctl status printer_host    │"
echo "  │  Logs:    journalctl -u printer_host -f         │"
echo "  └─────────────────────────────────────────────────┘"
echo ""

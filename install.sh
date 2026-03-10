#!/usr/bin/env bash
#
# ManualCTRL Printer Host – single-command installer for Raspberry Pi
# Usage:  curl -sSL <raw-url>/install.sh | bash
#    or:  chmod +x install.sh && ./install.sh
#
set -euo pipefail

REPO_URL="https://github.com/YOUR_USER/ManualCTRL_printer.git"
INSTALL_DIR="$HOME/ManualCTRL_printer"
KLIPPER_DIR="$HOME/klipper"
HOSTNAME="manualctrl"

echo "========================================="
echo "  ManualCTRL Printer Host – Installer"
echo "========================================="

# ── 1. System packages ──────────────────────────────────────
echo "[1/7] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git \
    build-essential libffi-dev libncurses-dev avrdude gcc-arm-none-eabi \
    binutils-arm-none-eabi libnewlib-arm-none-eabi stm32flash \
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

# ── 5. Klipper firmware compilation ─────────────────────────
echo "[5/7] Building Klipper firmware for SKR Mini E3 V3.0..."
if [ -d "$KLIPPER_DIR" ]; then
    cd "$KLIPPER_DIR" && git pull
else
    git clone https://github.com/Klipper3d/klipper.git "$KLIPPER_DIR"
fi
cd "$KLIPPER_DIR"

cp "$INSTALL_DIR/klipper.config" .config
make clean
make -j"$(nproc)"

FIRMWARE_OUT="$KLIPPER_DIR/out/klipper.bin"
if [ -f "$FIRMWARE_OUT" ]; then
    cp "$FIRMWARE_OUT" "$INSTALL_DIR/firmware.bin"
    echo "  Firmware built: $INSTALL_DIR/firmware.bin"
    echo "  Copy firmware.bin to an SD card, rename to firmware.bin,"
    echo "  insert into SKR Mini E3 V3.0, and power cycle the board."
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

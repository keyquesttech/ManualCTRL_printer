#!/usr/bin/env bash
#
# ManualCTRL Printer Host – Clean installer for Raspberry Pi
# Uses Arduino CLI to build firmware (works reliably on 32-bit ARM)
#
# Usage:  chmod +x install.sh && ./install.sh
#
set -euo pipefail

REPO_URL="https://github.com/keyquesttech/ManualCTRL_printer.git"
INSTALL_DIR="$HOME/ManualCTRL_printer"
HOSTNAME="manualctrl"
ARDUINO_CLI_DIR="$HOME/.local/bin"
FQBN="STMicroelectronics:stm32:GenG0:pnum=GENERIC_G0B1VETX,usb=CDCgen"
STM32_BOARD_URL="https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json"

echo "========================================="
echo "  ManualCTRL Printer Host – Installer"
echo "========================================="

# ── 0. Clean previous installs ────────────────────────────
echo ""
echo "[0/7] Cleaning previous installation artifacts..."
sudo systemctl stop printer_host 2>/dev/null || true
sudo systemctl disable printer_host 2>/dev/null || true
sudo rm -f /etc/systemd/system/printer_host.service
sudo systemctl daemon-reload 2>/dev/null || true
rm -rf "$HOME/.platformio"
rm -rf "$HOME/.arduino15"
rm -rf "$HOME/Arduino"
rm -f "$ARDUINO_CLI_DIR/arduino-cli"
echo "  Clean slate ready."

# ── 1. System packages ──────────────────────────────────
echo ""
echo "[1/7] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    git curl \
    gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi \
    exuberant-ctags \
    avahi-daemon avahi-utils libnss-mdns

# ── 2. Set hostname for mDNS (manualctrl.local) ─────────
echo ""
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

# ── 3. Clone the project ────────────────────────────────
echo ""
echo "[3/7] Cloning project repository..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  Directory exists – pulling latest..."
    cd "$INSTALL_DIR" && git pull
else
    rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ── 4. Python virtual environment ───────────────────────
echo ""
echo "[4/7] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ── 5. Build firmware with Arduino CLI ──────────────────
echo ""
echo "[5/7] Building ManualCTRL firmware for SKR Mini E3 V3.0..."

mkdir -p "$ARDUINO_CLI_DIR"
export PATH="$ARDUINO_CLI_DIR:$PATH"

echo "  Installing Arduino CLI..."
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR="$ARDUINO_CLI_DIR" sh

echo "  Adding STM32 board support (this may take a few minutes)..."
arduino-cli config init --overwrite
arduino-cli config add board_manager.additional_urls "$STM32_BOARD_URL"
arduino-cli core update-index
arduino-cli core install STMicroelectronics:stm32

echo "  Installing libraries..."
arduino-cli lib install "TMCStepper"
arduino-cli lib install "AccelStepper"

# On 32-bit ARM Pi the xpack toolchain downloaded by Arduino CLI is an x86
# binary that cannot execute.  Replace it with symlinks to the system's
# arm-none-eabi-* tools which ARE native armhf binaries.
ARCH=$(uname -m)
if [ "$ARCH" = "armv7l" ] || [ "$ARCH" = "armv6l" ]; then
    echo "  32-bit ARM detected — linking system ARM toolchain..."
    XPACK_DIR=$(find "$HOME/.arduino15/packages/STMicroelectronics/tools/xpack-arm-none-eabi-gcc" \
        -maxdepth 1 -mindepth 1 -type d 2>/dev/null | head -n1)
    if [ -n "$XPACK_DIR" ] && [ -d "$XPACK_DIR" ]; then
        rm -rf "$XPACK_DIR/bin"
        mkdir -p "$XPACK_DIR/bin"
        for f in /usr/bin/arm-none-eabi-*; do
            ln -sf "$f" "$XPACK_DIR/bin/"
        done
        [ -d /usr/arm-none-eabi ] && ln -sfn /usr/arm-none-eabi "$XPACK_DIR/arm-none-eabi"
        [ -d /usr/lib/arm-none-eabi ] && ln -sfn /usr/lib/arm-none-eabi "$XPACK_DIR/lib"
        [ -d /usr/lib/gcc/arm-none-eabi ] && ln -sfn /usr/lib/gcc/arm-none-eabi "$XPACK_DIR/gcc"
        echo "  System toolchain linked into Arduino CLI."
    else
        echo "  WARNING: Could not find xpack toolchain directory to patch."
    fi
    # Arduino CLI's builtin ctags is x86-only; use system ctags on 32-bit ARM.
    CTAGS_DIR="$HOME/.arduino15/packages/builtin/tools/ctags/5.8-arduino11"
    if [ -d "$CTAGS_DIR" ] && [ -x /usr/bin/ctags ]; then
        rm -f "$CTAGS_DIR/ctags"
        ln -sf /usr/bin/ctags "$CTAGS_DIR/ctags"
        echo "  System ctags linked for Arduino CLI."
    fi
fi

echo "  Compiling firmware..."
arduino-cli compile \
    --fqbn "$FQBN" \
    --build-property "build.flash_offset=0x2000" \
    --build-property "compiler.c.extra_flags=-DVECT_TAB_OFFSET=0x2000 -DUSBCON -DUSBD_USE_CDC -DHAL_PCD_MODULE_ENABLED -DSERIAL_RX_BUFFER_SIZE=256 -DSERIAL_TX_BUFFER_SIZE=256" \
    --build-property "compiler.cpp.extra_flags=-DVECT_TAB_OFFSET=0x2000 -DUSBCON -DUSBD_USE_CDC -DHAL_PCD_MODULE_ENABLED -DSERIAL_RX_BUFFER_SIZE=256 -DSERIAL_TX_BUFFER_SIZE=256" \
    --output-dir "$INSTALL_DIR/firmware/build" \
    "$INSTALL_DIR/firmware/ManualCTRL"

FIRMWARE_BIN="$INSTALL_DIR/firmware/build/ManualCTRL.ino.bin"
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

# ── 6. Systemd service ──────────────────────────────────
echo "[6/7] Installing systemd service..."
cd "$INSTALL_DIR"
sudo cp printer_host.service /etc/systemd/system/printer_host.service

sudo sed -i "s|User=pi|User=$USER|g" /etc/systemd/system/printer_host.service
sudo sed -i "s|/home/pi|$HOME|g" /etc/systemd/system/printer_host.service

sudo systemctl daemon-reload
sudo systemctl enable printer_host.service
sudo systemctl start printer_host.service

# ── 7. Done ──────────────────────────────────────────────
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
echo "  │  Update:  ~/ManualCTRL_printer/update.sh        │"
echo "  │  Remove:  ~/ManualCTRL_printer/uninstall.sh     │"
echo "  └─────────────────────────────────────────────────┘"
echo ""

#!/usr/bin/env bash
#
# ManualCTRL Printer Host – single-command updater
# Usage:  ./update.sh            (host code only)
#         ./update.sh --firmware  (also rebuild firmware)
#
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="printer_host"
ARDUINO_CLI_DIR="$HOME/.local/bin"
FQBN="STMicroelectronics:stm32:GenG0:pnum=GENERIC_G0B1VETX,usb=CDCgen"
BUILD_FW=false

for arg in "$@"; do
    case "$arg" in
        --firmware|-f) BUILD_FW=true ;;
    esac
done

echo "═══════════════════════════════════════"
echo "  ManualCTRL – Updater"
echo "═══════════════════════════════════════"

# ── 1. Pull latest from GitHub ──────────────────────────────
echo ""
echo "[1/4] Pulling latest from GitHub..."
cd "$INSTALL_DIR"

BEFORE=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
git fetch origin
git pull --ff-only origin main

AFTER=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
if [ "$BEFORE" = "$AFTER" ]; then
    echo "  Already up to date."
else
    echo "  Updated: ${BEFORE:0:8} → ${AFTER:0:8}"
    git --no-pager log --oneline "${BEFORE}..${AFTER}" 2>/dev/null | sed 's/^/    /'
fi

# ── 2. Update Python dependencies ───────────────────────────
echo ""
echo "[2/4] Checking Python dependencies..."
if [ -d "$INSTALL_DIR/venv" ]; then
    source "$INSTALL_DIR/venv/bin/activate"
    pip install -q --upgrade pip
    pip install -q -r "$INSTALL_DIR/requirements.txt"
    echo "  Dependencies up to date."
else
    echo "  WARNING: No venv found. Run install.sh first."
fi

# ── 3. Rebuild firmware (optional) ──────────────────────────
echo ""
if $BUILD_FW; then
    echo "[3/4] Rebuilding firmware with Arduino CLI..."
    export PATH="$ARDUINO_CLI_DIR:$PATH"

    if ! command -v arduino-cli &>/dev/null; then
        echo "  ERROR: Arduino CLI not found. Run install.sh first."
        exit 1
    fi

    arduino-cli lib upgrade

    # Patch xpack toolchain on 32-bit ARM (same as install.sh)
    ARCH=$(uname -m)
    if [ "$ARCH" = "armv7l" ] || [ "$ARCH" = "armv6l" ]; then
        XPACK_DIR=$(find "$HOME/.arduino15/packages/STMicroelectronics/tools/xpack-arm-none-eabi-gcc" \
            -maxdepth 1 -mindepth 1 -type d 2>/dev/null | head -n1)
        if [ -n "$XPACK_DIR" ] && [ -d "$XPACK_DIR" ] && ! "$XPACK_DIR/bin/arm-none-eabi-gcc" --version &>/dev/null; then
            echo "  Patching toolchain with system arm-none-eabi..."
            rm -rf "$XPACK_DIR/bin"
            mkdir -p "$XPACK_DIR/bin"
            for f in /usr/bin/arm-none-eabi-*; do ln -sf "$f" "$XPACK_DIR/bin/"; done
            [ -d /usr/arm-none-eabi ] && ln -sfn /usr/arm-none-eabi "$XPACK_DIR/arm-none-eabi"
            [ -d /usr/lib/arm-none-eabi ] && ln -sfn /usr/lib/arm-none-eabi "$XPACK_DIR/lib"
        fi
        CTAGS_DIR="$HOME/.arduino15/packages/builtin/tools/ctags/5.8-arduino11"
        if [ -d "$CTAGS_DIR" ] && [ -x /usr/bin/ctags ]; then
            rm -f "$CTAGS_DIR/ctags"
            ln -sf /usr/bin/ctags "$CTAGS_DIR/ctags"
        fi
    fi

    arduino-cli compile \
        --fqbn "$FQBN" \
        --build-property "build.flash_offset=0x2000" \
        --build-property "compiler.c.extra_flags=-DVECT_TAB_OFFSET=0x2000 -DUSBCON -DUSBD_USE_CDC -DHAL_PCD_MODULE_ENABLED -DSERIAL_RX_BUFFER_SIZE=256 -DSERIAL_TX_BUFFER_SIZE=256" \
        --build-property "compiler.cpp.extra_flags=-DVECT_TAB_OFFSET=0x2000 -DUSBCON -DUSBD_USE_CDC -DHAL_PCD_MODULE_ENABLED -DSERIAL_RX_BUFFER_SIZE=256 -DSERIAL_TX_BUFFER_SIZE=256" \
        --output-dir "$INSTALL_DIR/firmware/build" \
        "$INSTALL_DIR/firmware/ManualCTRL"

    FW="$INSTALL_DIR/firmware/build/ManualCTRL.ino.bin"
    if [ -f "$FW" ]; then
        cp "$FW" "$INSTALL_DIR/firmware.bin"
        echo "  Firmware built → ~/ManualCTRL_printer/firmware.bin"
        echo "  Flash: copy to SD card, insert into SKR, power cycle."
    else
        echo "  WARNING: Firmware build may have failed."
    fi
else
    echo "[3/4] Firmware rebuild skipped (use --firmware to rebuild)"
fi

# ── 4. Restart the service ──────────────────────────────────
echo ""
echo "[4/4] Restarting ${SERVICE_NAME}..."
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    sudo systemctl restart "$SERVICE_NAME"
    echo "  Service restarted."
elif systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    sudo systemctl start "$SERVICE_NAME"
    echo "  Service started."
else
    echo "  Service not installed — skipping. Start manually with:"
    echo "    cd $INSTALL_DIR && source venv/bin/activate && python main.py"
fi

# ── Done ────────────────────────────────────────────────────
echo ""
echo "Update complete!"
IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "?")
HOSTNAME_LOCAL=$(hostname 2>/dev/null || echo "manualctrl")
echo "  Web UI:  http://${HOSTNAME_LOCAL}.local:8000"
echo "  Network: http://${IP_ADDR}:8000"
echo "  Logs:    journalctl -u ${SERVICE_NAME} -f"
echo ""

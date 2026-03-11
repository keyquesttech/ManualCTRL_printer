#!/usr/bin/env bash
#
# ManualCTRL Printer Host – Uninstaller
# Usage:  chmod +x uninstall.sh && ./uninstall.sh
#
set -euo pipefail

INSTALL_DIR="$HOME/ManualCTRL_printer"
SERVICE_NAME="printer_host"

echo "========================================="
echo "  ManualCTRL Printer Host – Uninstaller"
echo "========================================="
echo ""

# ── 1. Stop and remove systemd service ────────────────────
echo "[1/4] Removing systemd service..."
if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    sudo systemctl daemon-reload
    echo "  Service removed."
else
    echo "  Service not found — skipping."
fi

# ── 2. Remove Arduino CLI and its data ────────────────────
echo "[2/4] Removing Arduino CLI..."
rm -f "$HOME/.local/bin/arduino-cli"
rm -rf "$HOME/.arduino15"
rm -rf "$HOME/Arduino"
echo "  Arduino CLI removed."

# ── 3. Remove PlatformIO data (if any from previous installs) ─
echo "[3/4] Removing PlatformIO data..."
rm -rf "$HOME/.platformio"
echo "  PlatformIO data removed."

# ── 4. Remove project directory ───────────────────────────
echo "[4/4] Removing project files..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo "  Removed $INSTALL_DIR"
else
    echo "  Project directory not found — skipping."
fi

echo ""
echo "  ┌─────────────────────────────────────────────────┐"
echo "  │  ManualCTRL has been completely uninstalled.     │"
echo "  │                                                  │"
echo "  │  To reinstall:                                   │"
echo "  │    git clone https://github.com/keyquesttech/    │"
echo "  │      ManualCTRL_printer.git                      │"
echo "  │    cd ManualCTRL_printer                         │"
echo "  │    chmod +x install.sh && ./install.sh           │"
echo "  └─────────────────────────────────────────────────┘"
echo ""

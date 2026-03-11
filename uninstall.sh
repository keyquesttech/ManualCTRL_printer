#!/usr/bin/env bash
#
# ManualCTRL Printer Host – Full Uninstaller
# Removes ManualCTRL, Klipper, build tools, and all related data.
#
# Usage:  chmod +x uninstall.sh && ./uninstall.sh
#
set -euo pipefail

INSTALL_DIR="$HOME/ManualCTRL_printer"

echo "========================================="
echo "  ManualCTRL Printer Host – Uninstaller"
echo "========================================="
echo ""

# ── 1. Stop and remove ManualCTRL service ─────────────────
echo "[1/6] Removing ManualCTRL service..."
sudo systemctl stop printer_host 2>/dev/null || true
sudo systemctl disable printer_host 2>/dev/null || true
sudo rm -f /etc/systemd/system/printer_host.service
echo "  ManualCTRL service removed."

# ── 2. Stop and remove Klipper services ──────────────────
echo "[2/6] Removing Klipper (if installed)..."
for svc in klipper moonraker; do
    if systemctl list-unit-files 2>/dev/null | grep -q "$svc"; then
        sudo systemctl stop "$svc" 2>/dev/null || true
        sudo systemctl disable "$svc" 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/${svc}.service"
        echo "  Removed $svc service."
    fi
done
sudo systemctl daemon-reload

rm -rf "$HOME/klipper"
rm -rf "$HOME/klippy-env"
rm -rf "$HOME/moonraker"
rm -rf "$HOME/moonraker-env"
rm -rf "$HOME/printer_data"
rm -rf "$HOME/klipper_config"
rm -rf "$HOME/klipper_logs"
rm -rf "$HOME/gcode_files"
rm -rf "$HOME/mainsail"
rm -rf "$HOME/fluidd"
rm -rf "$HOME/KlipperScreen"
echo "  Klipper and related tools removed."

# ── 3. Remove Arduino CLI and its data ───────────────────
echo "[3/6] Removing Arduino CLI..."
rm -f "$HOME/.local/bin/arduino-cli"
rm -rf "$HOME/.arduino15"
rm -rf "$HOME/Arduino"
echo "  Arduino CLI removed."

# ── 4. Remove PlatformIO data ────────────────────────────
echo "[4/6] Removing PlatformIO..."
rm -rf "$HOME/.platformio"
echo "  PlatformIO removed."

# ── 5. Remove ManualCTRL project directory ────────────────
echo "[5/6] Removing project files..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo "  Removed $INSTALL_DIR"
else
    echo "  Project directory not found — skipping."
fi

# ── 6. Clean up leftover configs ─────────────────────────
echo "[6/6] Cleaning up..."
rm -f "$HOME/firmware.bin"
rm -rf "$HOME/gcode_logs"
rm -f "$HOME/printer.cfg"
rm -f "$HOME/printer.cfg.bak"
echo "  Cleanup done."

echo ""
echo "  ┌─────────────────────────────────────────────────┐"
echo "  │  Everything has been removed:                    │"
echo "  │    - ManualCTRL service + project files          │"
echo "  │    - Klipper / Moonraker / Mainsail / Fluidd    │"
echo "  │    - Arduino CLI + STM32 board data              │"
echo "  │    - PlatformIO data                             │"
echo "  │                                                  │"
echo "  │  To reinstall:                                   │"
echo "  │    git clone https://github.com/keyquesttech/    │"
echo "  │      ManualCTRL_printer.git                      │"
echo "  │    cd ManualCTRL_printer                         │"
echo "  │    chmod +x install.sh && ./install.sh           │"
echo "  └─────────────────────────────────────────────────┘"
echo ""

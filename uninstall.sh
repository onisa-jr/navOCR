#!/usr/bin/env bash
set -e

echo "Uninstalling navOcr..."

rm -f "$HOME/.local/bin/navocr"
rm -f "$HOME/.local/share/applications/navocr.desktop"

# Optional: Kill any running daemon
pkill -f "navocr.cli daemon" 2>/dev/null || true
rm -f "/tmp/navocr-$(id -u).sock" 2>/dev/null || true

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "[✓] navOcr has been uninstalled."
echo "Note: Configuration directory ~/.config/navocr was preserved. Delete manually if needed."

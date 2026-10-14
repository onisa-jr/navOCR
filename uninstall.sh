#!/usr/bin/env bash
set -e

echo "Uninstalling navOcr..."

rm -f "$HOME/.local/bin/navocr"
rm -f "$HOME/.local/share/applications/navocr.desktop"

# Restore default MATE screenshot handler if it was set to navocr
if command -v gsettings >/dev/null 2>&1; then
    if gsettings list-schemas | grep -q "org.mate.Marco"; then
        cmd="$(gsettings get org.mate.Marco.keybinding-commands command-screenshot 2>/dev/null || true)"
        if [[ "$cmd" == *"navocr"* ]]; then
            gsettings set org.mate.Marco.keybinding-commands command-screenshot "mate-screenshot"
            echo "[✓] Restored MATE PrintScreen key to default mate-screenshot."
        fi
    fi
fi

# Kill any running daemon
pkill -f "navocr.cli daemon" 2>/dev/null || true
rm -f "/tmp/navocr-$(id -u).sock" 2>/dev/null || true

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "[✓] navOcr has been uninstalled."
echo "Note: Configuration directory ~/.config/navocr was preserved. Delete manually if needed."

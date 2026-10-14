#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "=========================================="
echo "    Installing navOcr for Debian Linux    "
echo "=========================================="

mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$HOME/.config/navocr"

# 1. Install package into python environment
if [ -f "$HOME/envs/global/bin/pip" ]; then
    "$HOME/envs/global/bin/pip" install -e "$SCRIPT_DIR" --quiet
elif command -v pip3 >/dev/null 2>&1; then
    pip3 install -e "$SCRIPT_DIR" --quiet 2>/dev/null || true
fi

# 2. Symlink launcher into ~/.local/bin
ln -sf "$SCRIPT_DIR/bin/navocr" "$BIN_DIR/navocr"
chmod +x "$BIN_DIR/navocr"
echo "[✓] Installed executable to $BIN_DIR/navocr"

# 3. Update and install desktop file
cp "$SCRIPT_DIR/navocr.desktop" "$DESKTOP_DIR/navocr.desktop"
sed -i "s|Exec=.*|Exec=$BIN_DIR/navocr capture|" "$DESKTOP_DIR/navocr.desktop"
chmod +x "$DESKTOP_DIR/navocr.desktop"
echo "[✓] Installed desktop entry to $DESKTOP_DIR/navocr.desktop"

# 4. Update desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# 5. Automatically configure PrintScreen shortcut on MATE Desktop
if command -v gsettings >/dev/null 2>&1; then
    if gsettings list-schemas | grep -q "org.mate.Marco"; then
        gsettings set org.mate.Marco.keybinding-commands command-screenshot "$BIN_DIR/navocr capture"
        gsettings set org.mate.Marco.global-keybindings run-command-screenshot "Print"
        echo "[✓] Configured PrintScreen key to activate navOcr capture automatically!"
    fi
fi

echo ""
echo "=== Verification ==="
"$BIN_DIR/navocr" test

echo ""
echo "=========================================="
echo "      navOcr Installed Successfully!      "
echo "=========================================="
echo ""
echo "How to use:"
echo "  1. Press the [PrintScreen] key on your keyboard anytime"
echo "  2. Drag to select any area of your screen"
echo "  3. Text is highlighted with neon glow and is selectable"
echo "  4. Use the bottom toolbar to:"
echo "     - 📷 Copy Image to clipboard"
echo "     - 📄 Copy Text to clipboard"
echo "     - 💾 Save Screenshot to Pictures"
echo "     - Aa Select All text"
echo "     - ✕  Close (or press Esc)"
echo "=========================================="

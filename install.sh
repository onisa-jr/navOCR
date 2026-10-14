#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "========================================"
echo "    Installing navOcr for Debian Linux   "
echo "========================================"

mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$HOME/.config/navocr"

# 1. Install package into python environment
if [ -f "$HOME/envs/global/bin/pip" ]; then
    "$HOME/envs/global/bin/pip" install -e "$SCRIPT_DIR" --quiet
fi

# 2. Symlink launcher into ~/.local/bin
ln -sf "$SCRIPT_DIR/bin/navocr" "$BIN_DIR/navocr"
chmod +x "$BIN_DIR/navocr"
echo "[✓] Installed executable to $BIN_DIR/navocr"

# 2. Update and install desktop file
cp "$SCRIPT_DIR/navocr.desktop" "$DESKTOP_DIR/navocr.desktop"
sed -i "s|Exec=.*|Exec=$BIN_DIR/navocr capture|" "$DESKTOP_DIR/navocr.desktop"
chmod +x "$DESKTOP_DIR/navocr.desktop"
echo "[✓] Installed desktop entry to $DESKTOP_DIR/navocr.desktop"

# 3. Update desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo ""
echo "=== Verification ==="
"$BIN_DIR/navocr" test

echo ""
echo "========================================"
echo "      navOcr Installed Successfully!    "
echo "========================================"
echo ""
echo "Quick Commands:"
echo "  navocr capture : Take screenshot snip and select text (iPhone Live Text UX)"
echo "  navocr daemon  : Run background daemon listening for Super+Shift+T"
echo "  navocr test    : Run diagnostic self-test"
echo ""
echo "Configuring Desktop Global Shortcut in MATE / GNOME:"
echo "  1. Open 'Keyboard Shortcuts' (mate-keybinding-properties or gnome-control-center)"
echo "  2. Click 'Add' (Custom Shortcuts)"
echo "  3. Name:    navOcr"
echo "     Command: $BIN_DIR/navocr capture"
echo "     Shortcut: Super + Shift + T  (or your favorite shortcut)"
echo "========================================"

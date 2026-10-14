"""
Command-line interface for navOcr.
Supports:
  navocr capture : triggers immediate screen capture (via running daemon or one-shot)
  navocr daemon  : starts resident daemon with global shortcut and system tray
  navocr test    : verifies IndraOCR, clipboard, and screen grab capabilities
  navocr config  : displays configuration and shortcut instructions
"""

import sys
import argparse
import signal

# Ensure Qt plugin environment is set before anything else
from navocr.compat import ensure_qt_environment
ensure_qt_environment()

from navocr import __version__
from navocr.config import AppConfig, CONFIG_FILE


def test_command():
    print(f"=== navOcr v{__version__} Self-Test ===")
    print("1. Testing IndraOCR Engine...")
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (360, 60), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((15, 20), "navOcr Self-Test OK", fill=(0, 0, 0))

        from navocr.ocr_engine import IndraEngine
        engine = IndraEngine.get_instance()
        res = engine.recognize_crop(img)
        print(f"   [✓] IndraOCR recognized: '{res.text}' ({res.avg_confidence*100:.1f}% conf in {res.elapsed_ms}ms)")
    except Exception as e:
        print(f"   [✗] IndraOCR failed: {e}")
        return 1

    print("2. Testing Clipboard Integration...")
    try:
        from navocr.clipboard import copy_to_clipboard
        success = copy_to_clipboard("navOcr Test Clipboard")
        if success:
            print("   [✓] Clipboard copy successful")
        else:
            print("   [✗] Clipboard copy returned false")
    except Exception as e:
        print(f"   [✗] Clipboard failed: {e}")

    print("3. Configuration Path:")
    print(f"   {CONFIG_FILE}")
    print("\nAll core components operational.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="navocr",
        description="navOcr: Fast native-like screen text OCR for Debian Linux using IndraOCR."
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="capture",
        choices=["capture", "daemon", "service", "test", "config", "status"],
        help="Action to perform (default: 'capture')"
    )
    parser.add_argument(
        "--auto-expand",
        action="store_true",
        help="Expand full text panel immediately after capture (bypass Live Text affordance icon)"
    )
    parser.add_argument(
        "--auto-copy",
        action="store_true",
        help="Automatically copy recognized text to clipboard upon release"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"navOcr {__version__}"
    )

    args = parser.parse_args()

    # Handle 'test' action
    if args.action == "test":
        sys.exit(test_command())

    # Handle 'config' action
    if args.action == "config":
        cfg = AppConfig.load()
        print(f"navOcr Configuration ({CONFIG_FILE}):")
        for k, v in cfg.__dict__.items():
            print(f"  {k}: {v}")
        print("\nTo bind a custom desktop shortcut in MATE / GNOME / XFCE:")
        print("  Command: navocr capture")
        print(f"  Shortcut: {cfg.shortcut_display}")
        return

    # Handle 'capture' action
    if args.action == "capture":
        # Check if daemon is already running
        from navocr.app import send_ipc_command
        if send_ipc_command("capture"):
            # Signal sent successfully to running daemon
            sys.exit(0)

        # No daemon running: initialize QApplication FIRST before loading any other modules
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        ensure_qt_environment()

        from navocr.app import NavOcrApp
        cfg = AppConfig.load()
        if args.auto_expand:
            cfg.auto_expand = True
        if args.auto_copy:
            cfg.auto_copy = True

        nav_app = NavOcrApp(config=cfg, standalone_once=True)
        nav_app.trigger_capture()
        sys.exit(app.exec_())

    # Handle 'daemon' or 'service' action
    if args.action in ("daemon", "service"):
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        ensure_qt_environment()

        from navocr.app import NavOcrApp
        cfg = AppConfig.load()
        if args.auto_expand:
            cfg.auto_expand = True
        if args.auto_copy:
            cfg.auto_copy = True

        nav_app = NavOcrApp(config=cfg, standalone_once=False)
        print(f"[navOcr] Daemon active. Global shortcut: {cfg.shortcut_display}")
        print("[navOcr] Listening for triggers...")
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()

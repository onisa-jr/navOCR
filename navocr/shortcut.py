"""
Global keyboard shortcut listener for navOcr.
Uses pynput with thread-safe Qt signal dispatching.
"""

from PyQt5.QtCore import QObject, pyqtSignal
from pynput import keyboard
import threading
from typing import Optional


class GlobalShortcutListener(QObject):
    activated = pyqtSignal()

    def __init__(self, shortcut_pattern: str = "<cmd>+<shift>+t", parent=None):
        super().__init__(parent)
        self.shortcut_pattern = shortcut_pattern
        self.listener: Optional[keyboard.GlobalHotKeys] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        try:
            # Map shortcut pattern to on_trigger
            hotkeys = {
                self.shortcut_pattern: self._on_triggered
            }
            # Fallback alias for platforms where <cmd> is <super>
            if "<cmd>" in self.shortcut_pattern:
                alt_pattern = self.shortcut_pattern.replace("<cmd>", "<super>")
                hotkeys[alt_pattern] = self._on_triggered

            self.listener = keyboard.GlobalHotKeys(hotkeys)
            self.listener.daemon = True
            self.listener.start()
        except Exception as e:
            print(f"[navOcr] Note: Global hotkey registration: {e}")

    def _on_triggered(self):
        self.activated.emit()

    def stop(self):
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

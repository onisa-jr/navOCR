"""
Main Application coordinator for navOcr.
Manages selection overlay, in-memory OCR inference, Live Text image viewer,
single-instance IPC socket, and desktop integration.
"""

import os
import sys
import socket
import threading
from typing import Optional
from PIL import Image

from PyQt5.QtCore import Qt, QRect, pyqtSlot, QThread, pyqtSignal, QEvent
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QAction
)

from navocr.config import AppConfig
from navocr.ocr_engine import IndraEngine, OCRResult
from navocr.overlay import SelectionOverlay
from navocr.live_viewer import LiveTextImageViewer
from navocr.shortcut import GlobalShortcutListener
from navocr.clipboard import copy_to_clipboard
from navocr.theme import COLOR_ACCENT, COLOR_PANEL

SOCKET_PATH = f"/tmp/navocr-{os.getuid()}.sock"


class OCRWorker(QThread):
    finished = pyqtSignal(OCRResult, object, QRect)

    def __init__(self, engine: IndraEngine, crop: Image.Image, rect: QRect):
        super().__init__()
        self.engine = engine
        self.crop = crop
        self.rect = rect

    def run(self):
        result = self.engine.recognize_crop(self.crop)
        self.finished.emit(result, self.crop, self.rect)


class NavOcrApp:
    def __init__(self, config: Optional[AppConfig] = None, standalone_once: bool = False):
        self.config = config or AppConfig.load()
        self.standalone_once = standalone_once

        self.ocr_engine = IndraEngine.get_instance(threads=self.config.threads)

        self.overlay = SelectionOverlay(dim_opacity=self.config.dim_opacity)
        self.overlay.capture_done.connect(self.on_capture_done)
        self.overlay.cancelled.connect(self.on_capture_cancelled)

        self.active_viewer: Optional[LiveTextImageViewer] = None

        self.shortcut_listener: Optional[GlobalShortcutListener] = None
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = True

        if not self.standalone_once:
            self._setup_global_shortcut()
            self._setup_tray()
            self._start_ipc_server()

    def _setup_global_shortcut(self):
        self.shortcut_listener = GlobalShortcutListener(
            shortcut_pattern=self.config.shortcut
        )
        self.shortcut_listener.activated.connect(self.trigger_capture)
        self.shortcut_listener.start()

    def _create_tray_icon_pixmap(self) -> QPixmap:
        pix = QPixmap(32, 32)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(COLOR_PANEL))
        p.setPen(QColor(COLOR_ACCENT))
        p.drawRoundedRect(2, 2, 28, 28, 6, 6)
        p.setPen(QColor(COLOR_ACCENT))
        font = p.font()
        font.setBold(True)
        font.setPixelSize(14)
        p.setFont(font)
        p.drawText(pix.rect(), Qt.AlignCenter, "OCR")
        p.end()
        return pix

    def _setup_tray(self):
        if not self.config.show_tray_icon or not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon = QIcon(self._create_tray_icon_pixmap())
        self.tray_icon = QSystemTrayIcon(icon)
        self.tray_icon.setToolTip("navOcr - Live Screen Text Recognition")

        menu = QMenu()
        menu.setStyleSheet(f"background-color: {COLOR_PANEL}; color: white; border: 1px solid #1c2b22;")

        action_capture = QAction(f"Capture Screen ({self.config.shortcut_display})", menu)
        action_capture.triggered.connect(self.trigger_capture)
        menu.addAction(action_capture)

        menu.addSeparator()

        action_quit = QAction("Quit navOcr", menu)
        action_quit.triggered.connect(self.quit_app)
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.trigger_capture()

    def _start_ipc_server(self):
        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass

        def server_loop():
            try:
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server.bind(SOCKET_PATH)
                server.listen(5)
                while self.running:
                    server.settimeout(1.0)
                    try:
                        conn, _ = server.accept()
                    except socket.timeout:
                        continue
                    except Exception:
                        break

                    with conn:
                        data = conn.recv(128).decode("utf-8").strip()
                        if data == "capture":
                            QApplication.instance().postEvent(
                                self.overlay,
                                TriggerCaptureEvent()
                            )
                            conn.sendall(b"ok\n")
                        elif data == "quit":
                            conn.sendall(b"bye\n")
                            QApplication.instance().quit()
                            break
                        else:
                            conn.sendall(b"unknown\n")
            except Exception as e:
                print(f"[navOcr] Socket server info: {e}")

        self.server_thread = threading.Thread(target=server_loop, daemon=True)
        self.server_thread.start()

    @pyqtSlot()
    def trigger_capture(self):
        self.dismiss_viewer()
        self.overlay.show_overlay()

    def on_capture_cancelled(self):
        if self.standalone_once:
            QApplication.instance().quit()

    def on_capture_done(self, crop_image: Image.Image, selection_rect: QRect):
        # Run OCR in worker thread to keep UI completely responsive
        self.worker = OCRWorker(self.ocr_engine, crop_image, selection_rect)
        self.worker.finished.connect(self.on_ocr_finished)
        self.worker.start()

    def on_ocr_finished(self, result: OCRResult, crop_image: Image.Image, selection_rect: QRect):
        # Optional auto-copy behavior
        if self.config.auto_copy and not result.is_empty:
            copy_to_clipboard(result.text)

        # Display the captured image with selectable text in floating viewer
        self.active_viewer = LiveTextImageViewer(
            crop_image=crop_image,
            result=result,
            screen_rect=selection_rect
        )
        self.active_viewer.closed.connect(self.on_viewer_closed)
        self.active_viewer.show()
        self.active_viewer.raise_()
        self.active_viewer.activateWindow()

    def on_viewer_closed(self):
        self.active_viewer = None
        if self.standalone_once:
            QApplication.instance().quit()

    def dismiss_viewer(self):
        if self.active_viewer:
            self.active_viewer.close_viewer()
            self.active_viewer = None

    def quit_app(self):
        self.running = False
        if self.shortcut_listener:
            self.shortcut_listener.stop()
        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass
        QApplication.instance().quit()


class TriggerCaptureEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self):
        super().__init__(self.EVENT_TYPE)


def _custom_event(self, event):
    if event.type() == TriggerCaptureEvent.EVENT_TYPE:
        self.show_overlay()
        return True
    return SelectionOverlay.customEvent(self, event)


SelectionOverlay.customEvent = _custom_event


def send_ipc_command(command: str) -> bool:
    """Attempts to send a command to the running navOcr daemon."""
    if not os.path.exists(SOCKET_PATH):
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.5)
            s.connect(SOCKET_PATH)
            s.sendall(command.encode("utf-8"))
            resp = s.recv(128).decode("utf-8")
            return resp.strip() in ("ok", "bye")
    except Exception:
        return False

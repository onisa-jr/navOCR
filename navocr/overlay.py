"""
Fullscreen selection overlay for navOcr.
Captures a pristine, untouched screen grab BEFORE displaying the dimming overlay,
ensuring the cropped region retains 100% pure monitor colors with zero dimming tint
or selection border artifacts when copied or saved.
"""

from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QCursor, QPixmap, QImage
from PyQt5.QtWidgets import QWidget, QApplication
from PIL import ImageGrab, Image
from typing import Optional

from navocr.theme import (
    COLOR_CANVAS,
    COLOR_BORDER,
    COLOR_ACCENT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_TERTIARY,
    COLOR_PANEL,
    FONT_FAMILY
)


def qpixmap_to_pil(pix: QPixmap) -> Image.Image:
    """Converts a QPixmap to a PIL Image without disk overhead or format loss."""
    q_img = pix.toImage().convertToFormat(QImage.Format_RGBA8888)
    width = q_img.width()
    height = q_img.height()
    ptr = q_img.bits()
    ptr.setsize(q_img.byteCount())
    return Image.frombuffer("RGBA", (width, height), bytes(ptr), "raw", "RGBA", 0, 1)


class SelectionOverlay(QWidget):
    capture_done = pyqtSignal(object, QRect)  # (PIL.Image, QRect in screen coordinates)
    cancelled = pyqtSignal()

    def __init__(self, dim_opacity: float = 0.45, parent=None):
        super().__init__(parent)
        self.dim_opacity = dim_opacity

        # Window flags for fullscreen borderless on top
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)

        self.start_pos: Optional[QPoint] = None
        self.current_pos: Optional[QPoint] = None
        self.is_dragging = False

        self.pristine_pixmap: Optional[QPixmap] = None
        self.virtual_rect: QRect = QRect()

        self._calculate_desktop_geometry()

    def _calculate_desktop_geometry(self):
        """Calculates total virtual desktop bounding box across all monitors."""
        desktop = QApplication.desktop()
        self.virtual_rect = desktop.geometry()
        for i in range(desktop.screenCount()):
            self.virtual_rect = self.virtual_rect.united(desktop.screenGeometry(i))
        self.setGeometry(self.virtual_rect)

    def show_overlay(self):
        self._calculate_desktop_geometry()
        self.start_pos = None
        self.current_pos = None
        self.is_dragging = False

        # Grab pristine root screen pixels BEFORE overlay is rendered
        # Guarantees 100% monitor-accurate colors and exact pixel geometry
        try:
            screen = QApplication.primaryScreen()
            if screen:
                self.pristine_pixmap = screen.grabWindow(0)
            else:
                self.pristine_pixmap = None
        except Exception:
            self.pristine_pixmap = None

        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def get_selection_rect(self) -> QRect:
        if not self.start_pos or not self.current_pos:
            return QRect()
        x1, y1 = self.start_pos.x(), self.start_pos.y()
        x2, y2 = self.current_pos.x(), self.current_pos.y()
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        return QRect(left, top, width, height)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.globalPos()
            self.current_pos = self.start_pos
            self.is_dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.current_pos = event.globalPos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.current_pos = event.globalPos()
            rect = self.get_selection_rect()

            # Ignore tiny clicks / micro-drags (< 6px)
            if rect.width() < 6 or rect.height() < 6:
                self.hide()
                self.pristine_pixmap = None
                self.cancelled.emit()
                return

            self.hide()

            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

            # Crop directly from the pre-captured pristine screen
            try:
                if self.pristine_pixmap and not self.pristine_pixmap.isNull():
                    offset_x = self.virtual_rect.x() if self.virtual_rect.x() < 0 else 0
                    offset_y = self.virtual_rect.y() if self.virtual_rect.y() < 0 else 0

                    crop_x = max(0, x - offset_x)
                    crop_y = max(0, y - offset_y)
                    crop_w = min(self.pristine_pixmap.width() - crop_x, w)
                    crop_h = min(self.pristine_pixmap.height() - crop_y, h)

                    if crop_w > 0 and crop_h > 0:
                        crop_pix = self.pristine_pixmap.copy(crop_x, crop_y, crop_w, crop_h)
                        crop_img = qpixmap_to_pil(crop_pix)
                    else:
                        raise ValueError("Invalid crop bounds")
                else:
                    QApplication.processEvents()
                    crop_img = ImageGrab.grab(bbox=(x, y, x + w, y + h))

                self.pristine_pixmap = None
                self.capture_done.emit(crop_img, rect)
            except Exception:
                self.pristine_pixmap = None
                self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.is_dragging = False
            self.pristine_pixmap = None
            self.hide()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        sel_rect = self.get_selection_rect()

        # 1. Draw dimmed mask over everything EXCEPT the selected rectangle
        dim_color = QColor(10, 15, 13, int(255 * self.dim_opacity))
        full_path = QPainterPath()
        full_path.addRect(0, 0, self.width(), self.height())

        if not sel_rect.isEmpty():
            sel_path = QPainterPath()
            sel_path.addRect(sel_rect.x(), sel_rect.y(), sel_rect.width(), sel_rect.height())
            draw_path = full_path.subtracted(sel_path)
            painter.fillPath(draw_path, QBrush(dim_color))

            # 2. Draw subtle selection accent border on screen during drag
            # (Note: This border is NOT in the final crop because the crop is taken from pristine_screen!)
            painter.fillRect(sel_rect, QColor(74, 222, 128, 10))
            pen = QPen(QColor(COLOR_ACCENT), 1.5)
            painter.setPen(pen)
            painter.drawRect(sel_rect)

            # 3. Floating Dimension Badge
            dim_text = f"{sel_rect.width()} × {sel_rect.height()}"
            font = QFont(FONT_FAMILY, 9)
            font.setBold(True)
            painter.setFont(font)

            badge_w, badge_h = 75, 20
            badge_x = sel_rect.x() + (sel_rect.width() - badge_w) // 2
            badge_y = sel_rect.y() + sel_rect.height() + 6
            if badge_y + badge_h > self.height() - 10:
                badge_y = sel_rect.y() - badge_h - 6

            badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(18, 24, 21, 220))
            painter.drawRoundedRect(badge_rect, 4, 4)

            painter.setPen(QPen(QColor(COLOR_BORDER)))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(badge_rect, 4, 4)

            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.drawText(badge_rect, Qt.AlignCenter, dim_text)
        else:
            painter.fillPath(full_path, QBrush(dim_color))

        # 4. Instruction Banner (top center)
        hint_text = "Drag to capture  ·  Esc to cancel"
        font = QFont(FONT_FAMILY, 10)
        painter.setFont(font)
        hint_w, hint_h = 240, 28
        hint_x = (self.width() - hint_w) // 2
        hint_y = 32

        hint_rect = QRect(hint_x, hint_y, hint_w, hint_h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(18, 24, 21, 230))
        painter.drawRoundedRect(hint_rect, 6, 6)

        painter.setPen(QPen(QColor(COLOR_BORDER)))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(hint_rect, 6, 6)

        painter.setPen(QColor(COLOR_TEXT_TERTIARY))
        painter.drawText(hint_rect, Qt.AlignCenter, hint_text)

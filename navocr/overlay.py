"""
Fullscreen selection overlay for navOcr.
Handles dimming, crosshair cursor, rubberband rectangular selection in any direction,
dimension tooltip, instructions, and capture cropping.
"""

from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QCursor
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

        self._calculate_desktop_geometry()

    def _calculate_desktop_geometry(self):
        """Calculates total virtual desktop bounding box across all monitors."""
        desktop = QApplication.desktop()
        virtual_rect = desktop.geometry()
        # Fallback to union of all screens if needed
        for i in range(desktop.screenCount()):
            virtual_rect = virtual_rect.united(desktop.screenGeometry(i))
        self.setGeometry(virtual_rect)

    def show_overlay(self):
        self._calculate_desktop_geometry()
        self.start_pos = None
        self.current_pos = None
        self.is_dragging = False
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
            rect = self.get_selection_rect()

            # Ignore tiny clicks / micro-drags
            if rect.width() < 6 or rect.height() < 6:
                self.hide()
                self.cancelled.emit()
                return

            # Hide overlay immediately before capturing so the overlay lines aren't in the crop
            self.hide()
            QApplication.processEvents()

            # Perform high-speed in-memory screen grab
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
            try:
                # ImageGrab.grab takes bounding box (left, upper, right, lower)
                crop_img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                self.capture_done.emit(crop_img, rect)
            except Exception as e:
                self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.is_dragging = False
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

            # 2. Draw subtle selection fill and sharp accent border
            painter.fillRect(sel_rect, QColor(74, 222, 128, 12))  # subtle 5% accent tint
            pen = QPen(QColor(COLOR_ACCENT), 1.5)
            painter.setPen(pen)
            painter.drawRect(sel_rect)

            # 3. Floating Dimension Badge
            dim_text = f"{sel_rect.width()} × {sel_rect.height()}"
            font = QFont(FONT_FAMILY, 9)
            font.setBold(True)
            painter.setFont(font)

            badge_w, badge_h = 75, 20
            # Place badge below selection or above if near bottom edge
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

        # 4. Instruction Banner (unobtrusive pill at top center)
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

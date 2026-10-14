"""
Live Text Interactive Image Viewer for navOcr.
Features continuous document-like text selection over the screenshot,
animated optical neon-green illumination, and sleek icon-based toolbar
with camera (image copy), text copy, save, and select-all actions.
"""

import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Tuple
from PIL import Image

from PyQt5.QtCore import Qt, QRectF, QPointF, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPixmap,
    QImage,
    QPainterPath,
    QLinearGradient,
    QKeySequence,
    QIcon
)
from PyQt5.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QShortcut,
    QApplication,
    QGraphicsDropShadowEffect
)

from navocr.theme import (
    COLOR_CANVAS,
    COLOR_PANEL,
    COLOR_HOVER,
    COLOR_BORDER,
    COLOR_BORDER_ACTIVE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_TERTIARY,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT,
    COLOR_ACCENT_TEXT,
    COLOR_NEON_PRIMARY,
    COLOR_NEON_GLOW
)
from navocr.ocr_engine import OCRResult, LineResult
from navocr.clipboard import copy_to_clipboard, copy_image_to_clipboard


def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Converts a PIL Image to QPixmap."""
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "RGBA")
    q_img = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(q_img)


# Vector Icon Generators
def make_camera_icon(color=QColor("#c7d3cc")) -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(color, 1.8))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(4, 9, 24, 16), 3, 3)
    p.drawEllipse(QRectF(11, 12.5, 10, 10))
    p.drawRoundedRect(QRectF(9, 6, 6, 3), 1, 1)
    p.end()
    return QIcon(pix)


def make_copy_text_icon(color=QColor("#c7d3cc")) -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(color, 1.6))
    p.setBrush(Qt.NoBrush)
    # Back sheet
    p.drawRoundedRect(QRectF(11, 5, 15, 18), 2, 2)
    # Front sheet
    p.setBrush(QColor("#121815"))
    p.drawRoundedRect(QRectF(6, 9, 15, 18), 2, 2)
    # Text lines
    p.drawLine(10, 14, 17, 14)
    p.drawLine(10, 18, 17, 18)
    p.drawLine(10, 22, 14, 22)
    p.end()
    return QIcon(pix)


def make_select_all_icon(color=QColor("#c7d3cc")) -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(color, 1.4, Qt.DashLine))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(4, 4, 24, 24), 3, 3)
    p.setPen(QPen(color, 1.6, Qt.SolidLine))
    font = p.font()
    font.setPixelSize(12)
    font.setBold(True)
    p.setFont(font)
    p.drawText(QRectF(4, 4, 24, 24), Qt.AlignCenter, "Aa")
    p.end()
    return QIcon(pix)


def make_save_icon(color=QColor("#c7d3cc")) -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(color, 1.6))
    p.setBrush(Qt.NoBrush)
    # Tray
    p.drawPolyline([QPoint(6, 17), QPoint(6, 25), QPoint(26, 25), QPoint(26, 17)])
    # Down arrow
    p.drawLine(16, 6, 16, 18)
    p.drawLine(11, 13, 16, 18)
    p.drawLine(21, 13, 16, 18)
    p.end()
    return QIcon(pix)


def make_close_icon(color=QColor("#8fa398")) -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(color, 2.0))
    p.drawLine(10, 10, 22, 22)
    p.drawLine(22, 10, 10, 22)
    p.end()
    return QIcon(pix)


class ActionIconButton(QPushButton):
    """
    Compact 28x28 icon button that displays tooltip on hover and notifies
    parent toolbar to update status label with the action word.
    """
    hover_entered = pyqtSignal(str)
    hover_left = pyqtSignal()

    def __init__(self, icon: QIcon, tooltip_text: str, hover_desc: str, parent=None):
        super().__init__(parent)
        self.setIcon(icon)
        self.setToolTip(tooltip_text)
        self.hover_desc = hover_desc
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, event):
        self.hover_entered.emit(self.hover_desc)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_left.emit()
        super().leaveEvent(event)


@dataclass(order=True, frozen=True)
class DocPos:
    line_idx: int
    char_idx: int


class LiveTextCanvas(QWidget):
    """
    Renders the screenshot with:
    1. Continuous document-like text selection across lines/paragraphs
    2. Animated optical neon shimmer scanning sweep
    3. Smooth hover and selected states without hard bounding boxes
    """
    selection_changed = pyqtSignal(str, int)  # (selected_text, character_count)

    def __init__(self, pixmap: QPixmap, lines: List[LineResult], parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.lines = lines

        # Selection state: continuous character range
        self.anchor_pos: Optional[DocPos] = None
        self.lead_pos: Optional[DocPos] = None
        self.is_selecting = False

        # Visual hover state
        self.hover_line_idx: Optional[int] = None

        # Animated Neon Shimmer Sweep state
        self.sweep_phase = 0.0           # 0.0 to 1.0 looping position
        self.sweep_intensity = 1.0       # Dampened during active selection
        self.text_min_x = 0.0
        self.text_max_x = float(self.pixmap.width())
        self._calculate_text_bounds()

        # Build union path of all text lines for clipped sweep illumination
        self.text_clip_path = self._build_text_clip_path()

        # Animation timer (~35 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        if self.lines:
            self.anim_timer.start(28)

        self.setMouseTracking(True)
        self.setFixedSize(self.pixmap.size())

    def _calculate_text_bounds(self):
        if not self.lines:
            return
        xs = [ln.box[0] for ln in self.lines] + [ln.box[2] for ln in self.lines]
        self.text_min_x = max(0.0, min(xs) - 40.0)
        self.text_max_x = min(float(self.pixmap.width()), max(xs) + 40.0)

    def _build_text_clip_path() -> QPainterPath:
        pass

    def _build_text_clip_path(self) -> QPainterPath:
        path = QPainterPath()
        for ln in self.lines:
            x0, y0, x1, y1 = ln.box
            rect = QRectF(x0 - 2.0, y0 - 1.0, (x1 - x0) + 4.0, (y1 - y0) + 2.0)
            path.addRoundedRect(rect, 3.0, 3.0)
        return path

    def _on_anim_tick(self):
        if not self.isVisible() or not self.lines:
            return

        self.sweep_phase = (self.sweep_phase + 0.009) % 1.0
        target_intensity = 0.25 if self.is_selecting else 1.0
        self.sweep_intensity += (target_intensity - self.sweep_intensity) * 0.15
        self.update()

    def stop_animation(self):
        if self.anim_timer.isActive():
            self.anim_timer.stop()

    def _pos_to_docpos(self, pt: QPointF) -> DocPos:
        """Maps a mouse coordinate to the nearest character DocPos in reading order."""
        if not self.lines:
            return DocPos(0, 0)

        px, py = pt.x(), pt.y()

        # Find line with minimal vertical distance
        best_line_idx = 0
        min_v_dist = float("inf")

        for i, ln in enumerate(self.lines):
            y0, y1 = ln.box[1], ln.box[3]
            if y0 <= py <= y1:
                v_dist = 0.0
            elif py < y0:
                v_dist = y0 - py
            else:
                v_dist = py - y1

            if v_dist < min_v_dist:
                min_v_dist = v_dist
                best_line_idx = i

        target_line = self.lines[best_line_idx]
        char_idx = target_line.char_at_x(px)
        return DocPos(best_line_idx, char_idx)

    def _get_selection_range(self) -> Optional[Tuple[DocPos, DocPos]]:
        if self.anchor_pos is None or self.lead_pos is None:
            return None
        if self.anchor_pos == self.lead_pos:
            return None
        return min(self.anchor_pos, self.lead_pos), max(self.anchor_pos, self.lead_pos)

    def get_selected_text(self) -> str:
        """Returns the continuous text span currently selected."""
        sel_range = self._get_selection_range()
        if not sel_range:
            return ""

        start, end = sel_range

        if start.line_idx == end.line_idx:
            line_str = self.lines[start.line_idx].text
            return line_str[start.char_idx : end.char_idx]

        parts = []
        parts.append(self.lines[start.line_idx].text[start.char_idx :])
        for l in range(start.line_idx + 1, end.line_idx):
            parts.append(self.lines[l].text)
        parts.append(self.lines[end.line_idx].text[: end.char_idx])
        return "\n".join(parts)

    def has_selection(self) -> bool:
        return self._get_selection_range() is not None

    def select_all(self):
        if not self.lines:
            return
        last_idx = len(self.lines) - 1
        self.anchor_pos = DocPos(0, 0)
        self.lead_pos = DocPos(last_idx, len(self.lines[last_idx].text))
        self.update()
        self._emit_selection_changed()

    def clear_selection(self):
        self.anchor_pos = None
        self.lead_pos = None
        self.update()
        self._emit_selection_changed()

    def _emit_selection_changed(self):
        txt = self.get_selected_text()
        self.selection_changed.emit(txt, len(txt))

    # Mouse interaction
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            doc_pos = self._pos_to_docpos(pos)

            if event.modifiers() & Qt.ShiftModifier and self.anchor_pos is not None:
                self.lead_pos = doc_pos
            else:
                self.anchor_pos = doc_pos
                self.lead_pos = doc_pos

            self.is_selecting = True
            self.update()
            self._emit_selection_changed()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        doc_pos = self._pos_to_docpos(pos)
        target_line = self.lines[doc_pos.line_idx] if self.lines else None

        if target_line and (target_line.box[1] - 3.0) <= pos.y() <= (target_line.box[3] + 3.0):
            if (target_line.box[0] - 8.0) <= pos.x() <= (target_line.box[2] + 8.0):
                self.setCursor(Qt.IBeamCursor)
                if self.hover_line_idx != doc_pos.line_idx:
                    self.hover_line_idx = doc_pos.line_idx
                    self.update()
            else:
                self.setCursor(Qt.ArrowCursor)
                if self.hover_line_idx is not None:
                    self.hover_line_idx = None
                    self.update()
        else:
            self.setCursor(Qt.ArrowCursor)
            if self.hover_line_idx is not None:
                self.hover_line_idx = None
                self.update()

        if self.is_selecting and (event.buttons() & Qt.LeftButton):
            self.lead_pos = doc_pos
            self.update()
            self._emit_selection_changed()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_selecting = False
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.lines:
            doc_pos = self._pos_to_docpos(event.pos())
            line = self.lines[doc_pos.line_idx]
            s, e = line.word_range_at_char(doc_pos.char_idx)
            self.anchor_pos = DocPos(doc_pos.line_idx, s)
            self.lead_pos = DocPos(doc_pos.line_idx, e)
            self.update()
            self._emit_selection_changed()

    def mouseTripleClick(self, doc_pos: DocPos):
        if not self.lines:
            return
        line = self.lines[doc_pos.line_idx]
        self.anchor_pos = DocPos(doc_pos.line_idx, 0)
        self.lead_pos = DocPos(doc_pos.line_idx, len(line.text))
        self.update()
        self._emit_selection_changed()

    def leaveEvent(self, event):
        if self.hover_line_idx is not None:
            self.hover_line_idx = None
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Base Screenshot
        painter.drawPixmap(0, 0, self.pixmap)

        if not self.lines:
            return

        # 2. Subtle Optical Neon Ambient Glow
        painter.fillPath(self.text_clip_path, QBrush(QColor(57, 255, 138, 14)))

        # 3. Hover State on line
        if self.hover_line_idx is not None and self.hover_line_idx < len(self.lines):
            hover_line = self.lines[self.hover_line_idx]
            hx0, hy0, hx1, hy1 = hover_line.box
            hover_rect = QRectF(hx0 - 2.0, hy0 - 1.0, (hx1 - hx0) + 4.0, (hy1 - hy0) + 2.0)
            painter.fillRect(hover_rect, QColor(57, 255, 138, 22))

        # 4. Animated Scanning Shimmer Sweep
        if self.sweep_intensity > 0.05:
            span_w = (self.text_max_x - self.text_min_x) + 120.0
            sweep_x = self.text_min_x + self.sweep_phase * span_w - 60.0
            sweep_w = 90.0

            grad = QLinearGradient(sweep_x - sweep_w / 2, 0, sweep_x + sweep_w / 2, 0)
            alpha_peak = int(70 * self.sweep_intensity)
            alpha_trail = int(32 * self.sweep_intensity)

            grad.setColorAt(0.0, QColor(57, 255, 138, 0))
            grad.setColorAt(0.35, QColor(57, 255, 138, alpha_trail))
            grad.setColorAt(0.50, QColor(140, 255, 185, alpha_peak))
            grad.setColorAt(0.65, QColor(57, 255, 138, alpha_trail))
            grad.setColorAt(1.0, QColor(57, 255, 138, 0))

            painter.save()
            painter.setClipPath(self.text_clip_path)
            painter.fillRect(self.rect(), QBrush(grad))
            painter.restore()

        # 5. Continuous Document Selection Highlight
        sel_range = self._get_selection_range()
        if sel_range:
            start, end = sel_range
            highlight_color = QColor(57, 255, 138, 92)
            highlight_pen = QPen(QColor(57, 255, 138, 175), 1.0)
            painter.setBrush(QBrush(highlight_color))
            painter.setPen(highlight_pen)

            for l_idx in range(start.line_idx, end.line_idx + 1):
                line = self.lines[l_idx]
                y_top = line.box[1] - 1.0
                y_bot = line.box[3] + 1.0
                h = y_bot - y_top

                if start.line_idx == end.line_idx:
                    x_left = line.char_xs[start.char_idx] if line.char_xs else line.box[0]
                    x_right = line.char_xs[end.char_idx] if line.char_xs else line.box[2]
                elif l_idx == start.line_idx:
                    x_left = line.char_xs[start.char_idx] if line.char_xs else line.box[0]
                    x_right = line.box[2]
                elif l_idx == end.line_idx:
                    x_left = line.box[0]
                    x_right = line.char_xs[end.char_idx] if line.char_xs else line.box[2]
                else:
                    x_left = line.box[0]
                    x_right = line.box[2]

                w = max(2.0, x_right - x_left)
                sel_rect = QRectF(x_left, y_top, w, h)
                painter.drawRoundedRect(sel_rect, 3.0, 3.0)


class LiveTextImageViewer(QWidget):
    """
    Compact floating image viewer with continuous text selection,
    animated optical neon shimmer, deep elevation shadow,
    and icon-driven action toolbar (Camera, Copy Text, Save, Select All, Close).
    """
    closed = pyqtSignal()
    SHADOW_MARGIN = 22

    def __init__(self, crop_image: Image.Image, result: OCRResult, screen_rect, parent=None):
        super().__init__(parent)
        self.crop_image = crop_image
        self.result = result
        self.screen_rect = screen_rect

        self.pixmap = pil_to_qpixmap(crop_image)

        # Frameless floating window on top
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Drag window state
        self._is_moving = False
        self._drag_start_pos = None

        self._build_ui()
        self._setup_shortcuts()
        self._position_on_screen()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(
            self.SHADOW_MARGIN,
            self.SHADOW_MARGIN,
            self.SHADOW_MARGIN,
            self.SHADOW_MARGIN
        )
        outer_layout.setSpacing(0)

        # Main Card container with distinct border and elevated surface
        self.card = QFrame(self)
        self.card.setStyleSheet(f"""
            QFrame#viewerCard {{
                background-color: {COLOR_CANVAS};
                border: 1.5px solid {COLOR_BORDER_ACTIVE};
                border-radius: 8px;
            }}
        """)
        self.card.setObjectName("viewerCard")

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 1. Image Canvas with Continuous Live Text Selection
        self.canvas = LiveTextCanvas(self.pixmap, self.result.lines, self.card)
        self.canvas.selection_changed.connect(self._on_selection_changed)

        # Scroll area in case selection is larger than standard screen area
        desktop = QApplication.desktop()
        screen_geo = desktop.screenGeometry(self.screen_rect.topLeft())
        max_w = int(screen_geo.width() * 0.85)
        max_h = int(screen_geo.height() * 0.80)

        if self.pixmap.width() > max_w or self.pixmap.height() > max_h:
            scroll = QScrollArea(self.card)
            scroll.setWidget(self.canvas)
            scroll.setWidgetResizable(True)
            scroll.setMaximumSize(max_w, max_h)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet("background: transparent; border: none;")
            card_layout.addWidget(scroll)
        else:
            card_layout.addWidget(self.canvas)

        # 2. Sleek Minimal Toolbar with Icon Buttons
        toolbar = QFrame(self.card)
        toolbar.setFixedHeight(36)
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_PANEL};
                border-top: 1px solid {COLOR_BORDER};
                border-bottom-left-radius: 7px;
                border-bottom-right-radius: 7px;
            }}
            QPushButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_HOVER};
                border: 1px solid {COLOR_BORDER_ACTIVE};
            }}
            QPushButton:pressed {{
                background-color: #141a17;
            }}
            QPushButton#cameraBtn:hover {{
                background-color: #1c2b22;
                border: 1px solid {COLOR_ACCENT};
            }}
            QPushButton#closeBtn:hover {{
                background-color: #2d1818;
                border: 1px solid #7f1d1d;
            }}
        """)

        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(10, 0, 8, 0)
        tb_layout.setSpacing(4)

        # Status / Hover Description Label
        self.status_lbl = QLabel("Drag to select text · Esc to close", toolbar)
        self.status_lbl.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 11px;")
        tb_layout.addWidget(self.status_lbl)

        tb_layout.addStretch()

        # Action 1: Camera Icon Button (Copies the screenshot image directly)
        self.camera_btn = ActionIconButton(
            icon=make_camera_icon(),
            tooltip_text="Copy Image to Clipboard",
            hover_desc="Copy Image",
            parent=toolbar
        )
        self.camera_btn.setObjectName("cameraBtn")
        self.camera_btn.clicked.connect(self._on_copy_image)
        self.camera_btn.hover_entered.connect(self._on_btn_hover_entered)
        self.camera_btn.hover_left.connect(self._on_btn_hover_left)
        tb_layout.addWidget(self.camera_btn)

        # Action 2: Copy Text Icon Button (Copies selected text or all text)
        self.copy_text_btn = ActionIconButton(
            icon=make_copy_text_icon(),
            tooltip_text="Copy Text (Ctrl+C)",
            hover_desc="Copy Text",
            parent=toolbar
        )
        self.copy_text_btn.setObjectName("copyTextBtn")
        self.copy_text_btn.clicked.connect(self._on_copy_text)
        self.copy_text_btn.hover_entered.connect(self._on_btn_hover_entered)
        self.copy_text_btn.hover_left.connect(self._on_btn_hover_left)
        tb_layout.addWidget(self.copy_text_btn)

        # Action 3: Save Screenshot to File Icon Button
        self.save_btn = ActionIconButton(
            icon=make_save_icon(),
            tooltip_text="Save Image to File",
            hover_desc="Save Image",
            parent=toolbar
        )
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self._on_save_image)
        self.save_btn.hover_entered.connect(self._on_btn_hover_entered)
        self.save_btn.hover_left.connect(self._on_btn_hover_left)
        tb_layout.addWidget(self.save_btn)

        # Action 4: Select All Text Icon Button
        self.select_all_btn = ActionIconButton(
            icon=make_select_all_icon(),
            tooltip_text="Select All Text (Ctrl+A)",
            hover_desc="Select All",
            parent=toolbar
        )
        self.select_all_btn.setObjectName("selectAllBtn")
        self.select_all_btn.clicked.connect(self.canvas.select_all)
        self.select_all_btn.hover_entered.connect(self._on_btn_hover_entered)
        self.select_all_btn.hover_left.connect(self._on_btn_hover_left)
        tb_layout.addWidget(self.select_all_btn)

        # Action 5: Close Icon Button
        self.close_btn = ActionIconButton(
            icon=make_close_icon(),
            tooltip_text="Close (Esc)",
            hover_desc="Close (Esc)",
            parent=toolbar
        )
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.clicked.connect(self.close_viewer)
        self.close_btn.hover_entered.connect(self._on_btn_hover_entered)
        self.close_btn.hover_left.connect(self._on_btn_hover_left)
        tb_layout.addWidget(self.close_btn)

        card_layout.addWidget(toolbar)
        outer_layout.addWidget(self.card)

        # Deep, distinct elevation shadow to separate viewer from background screen
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(42)
        shadow.setColor(QColor(0, 0, 0, 235))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

    def _setup_shortcuts(self):
        # Escape dismisses viewer immediately
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.close_viewer)
        # Ctrl+C copies text
        QShortcut(QKeySequence.Copy, self, self._on_copy_text)
        # Ctrl+A selects all
        QShortcut(QKeySequence.SelectAll, self, self.canvas.select_all)
        # Ctrl+S saves image
        QShortcut(QKeySequence.Save, self, self._on_save_image)

    def _position_on_screen(self):
        self.adjustSize()
        desktop = QApplication.desktop()
        screen_geo = desktop.screenGeometry(self.screen_rect.topLeft())

        target_x = self.screen_rect.x() - self.SHADOW_MARGIN
        target_y = self.screen_rect.y() - self.SHADOW_MARGIN

        # Clamp within monitor boundaries so toolbar and full window remain visible
        target_x = max(screen_geo.left() + 4, min(target_x, screen_geo.right() - self.width() - 4))
        target_y = max(screen_geo.top() + 4, min(target_y, screen_geo.bottom() - self.height() - 4))

        self.move(target_x, target_y)

    def _get_default_status_text(self) -> str:
        selected_text = self.canvas.get_selected_text()
        if selected_text:
            words = selected_text.split()
            w_count = len(words)
            w_str = "word" if w_count == 1 else "words"
            return f"{w_count} {w_str} selected"
        return "Drag to select text · Esc to close"

    def _on_selection_changed(self, selected_text: str, char_count: int):
        self.status_lbl.setText(self._get_default_status_text())

    def _on_btn_hover_entered(self, desc: str):
        self.status_lbl.setText(desc)
        self.status_lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px; font-weight: 500;")

    def _on_btn_hover_left(self):
        self.status_lbl.setText(self._get_default_status_text())
        self.status_lbl.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 11px;")

    def _on_copy_image(self):
        """Copies the captured image to clipboard."""
        success = copy_image_to_clipboard(self.crop_image)
        if success:
            self._show_feedback_status("✓ Image copied to clipboard")

    def _on_copy_text(self):
        """Copies selected text or all recognized text."""
        selected_text = self.canvas.get_selected_text()
        text_to_copy = selected_text if selected_text else self.result.text.strip()
        if text_to_copy:
            copy_to_clipboard(text_to_copy)
            self._show_feedback_status("✓ Text copied to clipboard")

    def _on_save_image(self):
        """Saves screenshot to ~/Pictures/Screenshots/."""
        save_dir = os.path.expanduser("~/Pictures/Screenshots")
        try:
            os.makedirs(save_dir, exist_ok=True)
            filename = datetime.now().strftime("Screenshot_%Y%m%d_%H%M%S.png")
            filepath = os.path.join(save_dir, filename)
            self.crop_image.save(filepath, format="PNG")
            self._show_feedback_status(f"✓ Saved: {filename}")
        except Exception as e:
            self._show_feedback_status(f"Error saving: {e}")

    def _show_feedback_status(self, text: str):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {COLOR_NEON_PRIMARY}; font-size: 11px; font-weight: bold;")
        QTimer.singleShot(1800, self._reset_feedback_status)

    def _reset_feedback_status(self):
        self.status_lbl.setText(self._get_default_status_text())
        self.status_lbl.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 11px;")

    def close_viewer(self):
        self.canvas.stop_animation()
        self.hide()
        self.closed.emit()
        self.deleteLater()

    # Drag window by toolbar or padding
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_moving = True
            self._drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_moving and self._drag_start_pos is not None:
            self.move(event.globalPos() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_moving = False

"""
Live Text Interactive Image Viewer for navOcr.
Features continuous document-like text selection over the screenshot,
animated optical neon-green illumination, and sleek icon-based toolbar
with camera (image copy), text copy, save, and select-all actions.
"""

import os
import re
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from PIL import Image

from PyQt5.QtCore import Qt, QRectF, QPointF, QPoint, pyqtSignal, QTimer, QSize, QEvent
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
    QLineEdit,
    QShortcut,
    QApplication,
    QGraphicsDropShadowEffect,
    QSizePolicy
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
    COLOR_NEON_GLOW,
    COLOR_STATUS_ALERT
)
from navocr.ocr_engine import OCRResult, LineResult
from navocr.clipboard import copy_to_clipboard, copy_image_to_clipboard


def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Converts a PIL Image to QPixmap."""
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "RGBA")
    q_img = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888).copy()
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


def make_lens_icon(color=QColor("#c7d3cc")) -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(color, 2.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(6.5, 6.5, 12.0, 12.0))
    p.drawLine(QPointF(16.7, 16.7), QPointF(24.5, 24.5))
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


class SearchMatch:
    """Represents a matched occurrence that may span one or more lines."""
    def __init__(self, spans: List[Tuple[int, int, int]]):
        self.spans = spans  # list of (line_idx, start_char, end_char)

    def __iter__(self):
        # Allows unpacking as (l_idx, s_idx, e_idx) for backwards compatibility
        if self.spans:
            return iter(self.spans[0])
        return iter((0, 0, 0))

    def __getitem__(self, idx):
        if self.spans:
            return self.spans[0][idx]
        raise IndexError("SearchMatch has no spans")

    def __len__(self):
        return 3

    def __eq__(self, other):
        if isinstance(other, SearchMatch):
            return self.spans == other.spans
        if isinstance(other, (tuple, list)) and len(other) == 3 and self.spans:
            return self.spans[0] == tuple(other)
        return False

    def __repr__(self):
        return f"SearchMatch(spans={self.spans})"


class LiveTextCanvas(QWidget):
    """
    Renders the screenshot with:
    1. Continuous document-like text selection across lines/paragraphs
    2. Animated optical neon shimmer scanning sweep
    3. Smooth hover and selected states without hard bounding boxes
    4. Proportional scaling to fit available screen space without distortion
    """
    selection_changed = pyqtSignal(str, int)  # (selected_text, character_count)

    def __init__(self, pixmap: QPixmap, lines: List[LineResult], scale: float = 1.0, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.lines = lines
        self.scale = max(0.01, float(scale))

        # Scaled display dimensions
        self.display_w = round(self.pixmap.width() * self.scale)
        self.display_h = round(self.pixmap.height() * self.scale)

        if abs(self.scale - 1.0) > 1e-4:
            self.display_pixmap = self.pixmap.scaled(
                self.display_w,
                self.display_h,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )
        else:
            self.display_pixmap = self.pixmap

        # Selection state: continuous character range
        self.anchor_pos: Optional[DocPos] = None
        self.lead_pos: Optional[DocPos] = None
        self.is_selecting = False

        # Search query and matches state
        self.search_query: str = ""
        self.search_matches: List[SearchMatch] = []
        self.current_match_idx: int = -1

        # Visual hover state
        self.hover_line_idx: Optional[int] = None

        # Animated Neon Shimmer Sweep state
        self.sweep_phase = 0.0           # 0.0 to 1.0 looping position
        self.sweep_intensity = 1.0       # Dampened during active selection
        self.text_min_x = 0.0
        self.text_max_x = float(self.display_w)
        self._calculate_text_bounds()

        # Build union path of all text lines for clipped sweep illumination
        self.text_clip_path = self._build_text_clip_path()

        # Animation timer (~35 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        if self.lines:
            self.anim_timer.start(28)

        self.setMouseTracking(True)
        self.setFixedSize(self.display_w, self.display_h)

    def _calculate_text_bounds(self):
        if not self.lines:
            return
        s = self.scale
        xs = [ln.box[0] * s for ln in self.lines] + [ln.box[2] * s for ln in self.lines]
        self.text_min_x = max(0.0, min(xs) - 40.0 * s)
        self.text_max_x = min(float(self.display_w), max(xs) + 40.0 * s)

    def _build_text_clip_path(self) -> QPainterPath:
        path = QPainterPath()
        s = self.scale
        r = max(1.0, 3.0 * s)
        for ln in self.lines:
            x0, y0, x1, y1 = ln.box
            rect = QRectF((x0 - 2.0) * s, (y0 - 1.0) * s, ((x1 - x0) + 4.0) * s, ((y1 - y0) + 2.0) * s)
            path.addRoundedRect(rect, r, r)
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

        s = self.scale
        px = pt.x() / s
        py = pt.y() / s

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

    def _get_char_x(self, line: LineResult, char_idx: int) -> float:
        """Returns horizontal screen coordinate (unscaled) for char_idx."""
        text_len = len(line.text) if line.text else 0
        if text_len == 0:
            return line.box[0]

        clamped_idx = max(0, min(text_len, char_idx))

        if line.char_xs:
            if len(line.char_xs) >= text_len + 1:
                return line.char_xs[clamped_idx]
            elif len(line.char_xs) == text_len:
                if clamped_idx < text_len:
                    return line.char_xs[clamped_idx]
                return line.box[2]
            elif len(line.char_xs) > 0:
                idx = min(clamped_idx, len(line.char_xs) - 1)
                return line.char_xs[idx]

        w_box = line.box[2] - line.box[0]
        return line.box[0] + (clamped_idx / text_len) * w_box

    # Search functions
    def set_search_query(self, query: str) -> int:
        """Finds all occurrences of query in recognized text lines and updates highlights."""
        clean_query = query.strip()
        self.search_query = clean_query
        self.search_matches = []
        self.current_match_idx = -1

        if clean_query and self.lines:
            # 1. Build document character map linking each character in doc_text back to (line_idx, char_idx)
            doc_chars: List[Tuple[int, Optional[int], str]] = []
            for l_idx, line in enumerate(self.lines):
                line_text = line.text or ""
                for c_idx, ch in enumerate(line_text):
                    doc_chars.append((l_idx, c_idx, ch))
                if l_idx < len(self.lines) - 1:
                    doc_chars.append((l_idx, None, "\n"))

            doc_text = "".join(ch for _, _, ch in doc_chars)

            # 2. Compile query into flexible whitespace regex
            words = [w for w in re.split(r'\s+', clean_query) if w]
            if words:
                regex_pattern = r'\s+'.join(re.escape(w) for w in words)
                try:
                    pattern = re.compile(regex_pattern, re.IGNORECASE)
                    for m in pattern.finditer(doc_text):
                        m_start, m_end = m.start(), m.end()
                        if m_start >= m_end:
                            continue

                        # Group matched character positions by line
                        line_spans_map: Dict[int, List[int]] = {}
                        for doc_i in range(m_start, m_end):
                            l_idx, c_idx, _ = doc_chars[doc_i]
                            if c_idx is not None:
                                if l_idx not in line_spans_map:
                                    line_spans_map[l_idx] = []
                                line_spans_map[l_idx].append(c_idx)

                        # For each line, compute exact [start_c, end_c] trimmed of line-boundary whitespace
                        match_spans: List[Tuple[int, int, int]] = []
                        for l_idx in sorted(line_spans_map.keys()):
                            c_indices = line_spans_map[l_idx]
                            if not c_indices:
                                continue
                            line_text = self.lines[l_idx].text or ""
                            s_char = min(c_indices)
                            e_char = max(c_indices) + 1

                            # Strictly trim any leading or trailing whitespace on this line
                            while s_char < e_char and line_text[s_char].isspace():
                                s_char += 1
                            while e_char > s_char and line_text[e_char - 1].isspace():
                                e_char -= 1

                            if s_char < e_char:
                                match_spans.append((l_idx, s_char, e_char))

                        if match_spans:
                            self.search_matches.append(SearchMatch(match_spans))
                except re.error:
                    pass

            if self.search_matches:
                self.current_match_idx = 0

        self.update()
        return len(self.search_matches)

    def next_search_match(self) -> int:
        if not self.search_matches:
            return -1
        self.current_match_idx = (self.current_match_idx + 1) % len(self.search_matches)
        self.update()
        return self.current_match_idx

    def prev_search_match(self) -> int:
        if not self.search_matches:
            return -1
        self.current_match_idx = (self.current_match_idx - 1) % len(self.search_matches)
        self.update()
        return self.current_match_idx

    def clear_search(self):
        self.search_query = ""
        self.search_matches = []
        self.current_match_idx = -1
        self.update()

    def get_match_rect(self, match_idx: int) -> Optional[QRectF]:
        if 0 <= match_idx < len(self.search_matches):
            match = self.search_matches[match_idx]
            spans = match.spans if hasattr(match, "spans") else [match]
            united_rect: Optional[QRectF] = None
            s = self.scale
            for (l_idx, s_idx, e_idx) in spans:
                if l_idx < len(self.lines):
                    line = self.lines[l_idx]
                    y_top = (line.box[1] - 1.0) * s
                    y_bot = (line.box[3] + 1.0) * s
                    h = max(2.0, y_bot - y_top)

                    x_left = self._get_char_x(line, s_idx) * s
                    x_right = self._get_char_x(line, e_idx) * s
                    w = max(1.0, x_right - x_left)
                    rect = QRectF(x_left, y_top, w, h)
                    if united_rect is None:
                        united_rect = rect
                    else:
                        united_rect = united_rect.united(rect)
            return united_rect
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "search_overlay"):
            self.search_overlay.reposition()

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

        s = self.scale
        orig_x = pos.x() / s
        orig_y = pos.y() / s

        if target_line and (target_line.box[1] - 3.0) <= orig_y <= (target_line.box[3] + 3.0):
            if (target_line.box[0] - 8.0) <= orig_x <= (target_line.box[2] + 8.0):
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
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 1. Base Screenshot
        painter.drawPixmap(0, 0, self.display_pixmap)

        if not self.lines:
            return

        s = self.scale
        r = max(1.5, 3.0 * s)

        # 2. Subtle Optical Neon Ambient Glow
        painter.fillPath(self.text_clip_path, QBrush(QColor(57, 255, 138, 14)))

        # 3. Hover State on line
        if self.hover_line_idx is not None and self.hover_line_idx < len(self.lines):
            hover_line = self.lines[self.hover_line_idx]
            hx0, hy0, hx1, hy1 = hover_line.box
            hover_rect = QRectF((hx0 - 2.0) * s, (hy0 - 1.0) * s, ((hx1 - hx0) + 4.0) * s, ((hy1 - hy0) + 2.0) * s)
            painter.fillRect(hover_rect, QColor(57, 255, 138, 22))

        # 4. Animated Scanning Shimmer Sweep
        if self.sweep_intensity > 0.05:
            span_w = (self.text_max_x - self.text_min_x) + 120.0 * s
            sweep_x = self.text_min_x + self.sweep_phase * span_w - 60.0 * s
            sweep_w = 90.0 * s

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

        # 5. Search Matches Highlight
        if self.search_matches:
            base_brush = QBrush(QColor(250, 204, 21, 115))
            base_pen = QPen(QColor(250, 204, 21, 220), 1.0)

            active_brush = QBrush(QColor(255, 230, 80, 175))
            active_pen = QPen(QColor(255, 255, 255, 240), 1.5)

            for idx, match in enumerate(self.search_matches):
                is_active = (idx == self.current_match_idx)
                brush = active_brush if is_active else base_brush
                pen = active_pen if is_active else base_pen

                spans = match.spans if hasattr(match, "spans") else [match]
                for (l_idx, s_idx, e_idx) in spans:
                    if l_idx >= len(self.lines):
                        continue
                    line = self.lines[l_idx]
                    y_top = (line.box[1] - 1.0) * s
                    y_bot = (line.box[3] + 1.0) * s
                    h = max(2.0, y_bot - y_top)

                    x_left = self._get_char_x(line, s_idx) * s
                    x_right = self._get_char_x(line, e_idx) * s
                    w = max(1.0, x_right - x_left)

                    r_corner = min(2.5 * s, max(1.0, w / 2.0))
                    m_rect = QRectF(x_left, y_top, w, h)

                    painter.setBrush(brush)
                    painter.setPen(pen)
                    painter.drawRoundedRect(m_rect, r_corner, r_corner)

        # 6. Continuous Document Selection Highlight
        sel_range = self._get_selection_range()
        if sel_range:
            start, end = sel_range
            highlight_color = QColor(57, 255, 138, 92)
            highlight_pen = QPen(QColor(57, 255, 138, 175), 1.0)
            painter.setBrush(QBrush(highlight_color))
            painter.setPen(highlight_pen)

            for l_idx in range(start.line_idx, end.line_idx + 1):
                line = self.lines[l_idx]
                y_top = (line.box[1] - 1.0) * s
                y_bot = (line.box[3] + 1.0) * s
                h = y_bot - y_top

                if start.line_idx == end.line_idx:
                    x_left = (line.char_xs[start.char_idx] if line.char_xs else line.box[0]) * s
                    x_right = (line.char_xs[end.char_idx] if line.char_xs else line.box[2]) * s
                elif l_idx == start.line_idx:
                    x_left = (line.char_xs[start.char_idx] if line.char_xs else line.box[0]) * s
                    x_right = line.box[2] * s
                elif l_idx == end.line_idx:
                    x_left = line.box[0] * s
                    x_right = (line.char_xs[end.char_idx] if line.char_xs else line.box[2]) * s
                else:
                    x_left = line.box[0] * s
                    x_right = line.box[2] * s

                w = max(2.0, x_right - x_left)
                sel_rect = QRectF(x_left, y_top, w, h)
                painter.drawRoundedRect(sel_rect, r, r)


class SearchOverlay(QFrame):
    """
    Floating lens search overlay in the top-right corner of the viewer.
    - Initially collapsed: shows only a sleek lens icon button.
    - When clicked: expands into an area for typing to search words in the image.
    - Real-time optical highlighting of matched words across the canvas.
    - ESC or clicking lens/close button collapses the typing area and clears highlights.
    """
    def __init__(self, canvas: LiveTextCanvas, parent=None):
        super().__init__(parent if parent is not None else canvas)
        self.canvas = canvas
        self.is_expanded = False

        self.setObjectName("searchOverlay")
        self.setAttribute(Qt.WA_Hover, True)

        self._build_ui()
        self._apply_style()
        self.collapse(clear_text=True)

    def _build_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(3, 3, 3, 3)
        self.layout.setSpacing(4)

        # Lens icon button (toggles open/closed)
        self.lens_btn = QPushButton(self)
        self.lens_btn.setIcon(make_lens_icon())
        self.lens_btn.setIconSize(QSize(18, 18))
        self.lens_btn.setFixedSize(26, 26)
        self.lens_btn.setCursor(Qt.PointingHandCursor)
        self.lens_btn.setToolTip("Search text in image (Ctrl+F)")
        self.lens_btn.clicked.connect(self.toggle_expand)
        self.layout.addWidget(self.lens_btn)

        # Typing area (QLineEdit)
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Find text...")
        self.search_input.setFixedHeight(24)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_return_pressed)
        self.search_input.installEventFilter(self)
        self.layout.addWidget(self.search_input)

        # Match count badge (e.g., "2/5" or "0")
        self.count_lbl = QLabel(self)
        self.count_lbl.setAlignment(Qt.AlignCenter)
        self.count_lbl.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 11px; font-weight: 500; padding: 0 2px;")
        self.layout.addWidget(self.count_lbl)

        # Close button ("×")
        self.close_btn = QPushButton("×", self)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setToolTip("Close search (Esc)")
        self.close_btn.clicked.connect(lambda: self.collapse(clear_text=True))
        self.layout.addWidget(self.close_btn)

    def _apply_style(self):
        border_css = f"1.5px solid {COLOR_ACCENT}" if self.is_expanded else f"1px solid {COLOR_BORDER}"
        bg_css = "rgba(18, 24, 21, 0.96)" if self.is_expanded else "rgba(18, 24, 21, 0.88)"
        self.setStyleSheet(f"""
            QFrame#searchOverlay {{
                background-color: {bg_css};
                border: {border_css};
                border-radius: 6px;
            }}
            QFrame#searchOverlay:hover {{
                background-color: rgba(26, 34, 30, 0.96);
                border: 1px solid {COLOR_BORDER_ACTIVE};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_HOVER};
            }}
            QLineEdit {{
                background-color: transparent;
                border: none;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 12px;
                selection-background-color: {COLOR_BORDER_ACTIVE};
                selection-color: {COLOR_TEXT_PRIMARY};
                padding: 0 4px;
            }}
            QPushButton#closeBtn {{
                color: {COLOR_TEXT_MUTED};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton#closeBtn:hover {{
                color: #ef4444;
                background-color: rgba(239, 68, 68, 0.15);
            }}
        """)
        self.close_btn.setObjectName("closeBtn")

    def toggle_expand(self):
        if self.is_expanded:
            self.collapse(clear_text=True)
        else:
            self.expand()

    def expand(self):
        self.is_expanded = True
        self.lens_btn.setIcon(make_lens_icon(QColor(COLOR_ACCENT)))
        self.search_input.show()
        self.count_lbl.show()
        self.close_btn.show()

        canvas_w = self.canvas.width() if self.canvas else 300
        max_available = max(60, canvas_w - 16)
        expanded_w = min(220, max_available)
        self.setFixedSize(expanded_w, 32)
        self._apply_style()
        self.reposition()
        self.search_input.setFocus()
        self.search_input.selectAll()
        if self.search_input.text():
            self._on_text_changed(self.search_input.text())

    def collapse(self, clear_text: bool = True):
        self.is_expanded = False
        self.lens_btn.setIcon(make_lens_icon(QColor("#c7d3cc")))
        self.search_input.hide()
        self.count_lbl.hide()
        self.close_btn.hide()

        self.setFixedSize(32, 32)
        self._apply_style()
        self.reposition()

        if clear_text:
            self.search_input.clear()
            self.count_lbl.setText("")
        if self.canvas:
            self.canvas.clear_search()
            self.canvas.setFocus()

    def reposition(self):
        if not self.canvas:
            return
        # Anchor strictly to the top-right corner of the displayed image (canvas)
        margin = 8
        x = self.canvas.width() - self.width() - margin
        y = margin
        self.move(max(margin, x), max(margin, y))
        self.raise_()

    def _on_text_changed(self, text: str):
        if not self.is_expanded:
            return
        total = self.canvas.set_search_query(text)
        self._update_count_display(total)

    def _on_return_pressed(self):
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.ShiftModifier:
            self.canvas.prev_search_match()
        else:
            self.canvas.next_search_match()
        self._update_count_display(len(self.canvas.search_matches))

    def _update_count_display(self, total: int):
        q = self.search_input.text().strip()
        if not q:
            self.count_lbl.setText("")
            return

        if total == 0:
            self.count_lbl.setText("0")
            self.count_lbl.setStyleSheet(f"color: {COLOR_STATUS_ALERT}; font-size: 11px; font-weight: 600; padding: 0 2px;")
        else:
            curr = self.canvas.current_match_idx + 1
            self.count_lbl.setText(f"{curr}/{total}")
            self.count_lbl.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: 600; padding: 0 2px;")

    def eventFilter(self, obj, event):
        if obj == self.search_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.collapse(clear_text=True)
                return True
        return super().eventFilter(obj, event)


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
        # Determine available desktop space accounting for dock/taskbars
        desktop = QApplication.desktop()
        screen_idx = desktop.screenNumber(self.screen_rect.topLeft())
        avail_geo = desktop.availableGeometry(screen_idx)

        # Available space accounting for usable screen area, shadows, margins, and toolbar
        screen_margin_x = 24
        screen_margin_y = 24
        toolbar_height = 36
        overhead_w = self.SHADOW_MARGIN * 2 + 4 + screen_margin_x
        overhead_h = self.SHADOW_MARGIN * 2 + toolbar_height + 4 + screen_margin_y

        available_width = max(160, avail_geo.width() - overhead_w)
        available_height = max(100, avail_geo.height() - overhead_h)

        img_w = max(1, self.pixmap.width())
        img_h = max(1, self.pixmap.height())

        # Exact proportional scale: 1:1 if it fits, scaled down proportionally if larger, never enlarged
        self.scale = min(1.0, available_width / img_w, available_height / img_h)
        self.display_w = round(img_w * self.scale)
        self.display_h = round(img_h * self.scale)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(
            self.SHADOW_MARGIN,
            self.SHADOW_MARGIN,
            self.SHADOW_MARGIN,
            self.SHADOW_MARGIN
        )
        outer_layout.setSpacing(0)

        # Set card size and window size with exact dimensions (no collapse or squashing)
        card_w = max(self.display_w, 176)
        card_h = self.display_h + toolbar_height

        win_w = card_w + self.SHADOW_MARGIN * 2
        win_h = card_h + self.SHADOW_MARGIN * 2
        self.setFixedSize(win_w, win_h)

        # Main Card container with distinct border and elevated surface
        self.card = QFrame(self)
        self.card.setFixedSize(card_w, card_h)
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

        # 1. Image Canvas with Continuous Live Text Selection (100% visible, no scrolling)
        self.canvas = LiveTextCanvas(self.pixmap, self.result.lines, scale=self.scale, parent=self.card)
        self.canvas.selection_changed.connect(self._on_selection_changed)
        card_layout.addWidget(self.canvas, 0, Qt.AlignCenter)

        # Floating search lens overlay anchored directly to the canvas (the displayed image)
        self.search_overlay = SearchOverlay(canvas=self.canvas, parent=self.canvas)
        self.canvas.search_overlay = self.search_overlay
        self.search_overlay.show()

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

        # Status / Hover Description Label (shrinks smoothly without forcing card width)
        self.status_lbl = QLabel("Drag to select text · Esc to close", toolbar)
        self.status_lbl.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 11px;")
        self.status_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.status_lbl.setMinimumWidth(0)
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
        # Escape dismisses search if expanded, otherwise dismisses viewer
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._on_escape)
        # Ctrl+C copies text
        QShortcut(QKeySequence.Copy, self, self._on_copy_text)
        # Ctrl+A selects all
        QShortcut(QKeySequence.SelectAll, self, self._on_select_all)
        # Ctrl+S saves image
        QShortcut(QKeySequence.Save, self, self._on_save_image)
        # Ctrl+F toggles search input
        QShortcut(QKeySequence.Find, self, self.toggle_search)

    def toggle_search(self):
        if hasattr(self, "search_overlay"):
            self.search_overlay.toggle_expand()

    def _on_escape(self):
        if hasattr(self, "search_overlay") and self.search_overlay.is_expanded:
            self.search_overlay.collapse(clear_text=True)
        else:
            self.close_viewer()

    def _on_select_all(self):
        if hasattr(self, "search_overlay") and self.search_overlay.search_input.hasFocus():
            self.search_overlay.search_input.selectAll()
            return
        self.canvas.select_all()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "search_overlay"):
            self.search_overlay.reposition()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "search_overlay"):
            self.search_overlay.reposition()

    def _position_on_screen(self):
        desktop = QApplication.desktop()
        screen_idx = desktop.screenNumber(self.screen_rect.topLeft())
        avail_geo = desktop.availableGeometry(screen_idx)

        # Center the viewer on the available screen area (accounting for desktop dock / taskbar)
        center_x = avail_geo.x() + (avail_geo.width() - self.width()) // 2
        center_y = avail_geo.y() + (avail_geo.height() - self.height()) // 2

        # Clamp strictly within usable monitor boundaries
        target_x = max(avail_geo.left(), min(center_x, avail_geo.right() - self.width()))
        target_y = max(avail_geo.top(), min(center_y, avail_geo.bottom() - self.height()))

        self.move(target_x, target_y)
        if hasattr(self, "search_overlay"):
            self.search_overlay.reposition()

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
        if hasattr(self, "search_overlay") and self.search_overlay.search_input.hasFocus():
            self.search_overlay.search_input.copy()
            return
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

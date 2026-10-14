"""
OCR Engine wrapper for IndraOCR.
Processes cropped PIL images directly in memory into structured lines,
character geometry, and reading layout.
"""

import time
import re
import numpy as np
from PIL import Image
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from navocr.compat import ensure_qt_environment


def _char_weight(c: str) -> float:
    """Relative typographic character width factor for proportional font estimation."""
    if c in 'ijl|!;:.,\'" ':
        return 0.5
    elif c in 'mwMW@%#':
        return 1.4
    elif c.isupper():
        return 1.2
    return 1.0


@dataclass
class LineResult:
    text: str
    box: List[float]  # [x0, y0, x1, y1] in crop coordinates
    conf: float
    char_xs: List[float] = field(default_factory=list)  # len(text) + 1 character boundary x coordinates

    def char_at_x(self, px: float) -> int:
        """Finds the character index closest to a horizontal pixel coordinate."""
        if not self.char_xs or px <= self.char_xs[0]:
            return 0
        if px >= self.char_xs[-1]:
            return len(self.text)
        low, high = 0, len(self.char_xs) - 1
        while low <= high:
            mid = (low + high) // 2
            if self.char_xs[mid] < px:
                low = mid + 1
            else:
                high = mid - 1
        idx1 = max(0, min(len(self.char_xs) - 1, low - 1))
        idx2 = max(0, min(len(self.char_xs) - 1, low))
        if abs(px - self.char_xs[idx1]) <= abs(px - self.char_xs[idx2]):
            return idx1
        return idx2

    def word_range_at_char(self, char_idx: int) -> Tuple[int, int]:
        """Finds the (start_char, end_char) word boundaries around char_idx."""
        L = len(self.text)
        if L == 0:
            return 0, 0
        c = max(0, min(L - 1, char_idx))
        if not self.text[c].isalnum():
            if c > 0 and self.text[c - 1].isalnum():
                c -= 1
            elif c < L - 1 and self.text[c + 1].isalnum():
                c += 1
        s = c
        while s > 0 and (self.text[s - 1].isalnum() or self.text[s - 1] in "_-"):
            s -= 1
        e = c
        while e < L and (self.text[e].isalnum() or self.text[e] in "_-"):
            e += 1
        return s, max(s + 1, e)


@dataclass
class OCRResult:
    text: str
    markdown: str
    lines: List[LineResult] = field(default_factory=list)
    word_count: int = 0
    line_count: int = 0
    avg_confidence: float = 0.0
    elapsed_ms: float = 0.0
    error: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        return not self.text or not self.text.strip()


class IndraEngine:
    _instance: Optional["IndraEngine"] = None

    def __init__(self, threads: int = 4):
        self.threads = threads
        self.converter = None
        self._initialize()

    def _initialize(self):
        try:
            import indra_ocr
            ensure_qt_environment()
            self.converter = indra_ocr.load(threads=self.threads)
        except Exception as e:
            self.converter = None
            raise RuntimeError(f"Failed to load IndraOCR: {e}")

    @classmethod
    def get_instance(cls, threads: int = 4) -> "IndraEngine":
        if cls._instance is None:
            cls._instance = cls(threads=threads)
        return cls._instance

    def recognize_crop(self, pil_image: Image.Image) -> OCRResult:
        """
        Runs OCR directly in memory on a PIL Image crop.
        Returns line results and continuous character geometry.
        """
        t0 = time.perf_counter()

        if pil_image is None or pil_image.width < 3 or pil_image.height < 3:
            return OCRResult(
                text="",
                markdown="",
                elapsed_ms=0.0,
                error="Selected region too small"
            )

        try:
            gray = np.array(pil_image.convert("L"))
            page = self.converter.ocr(gray, turn=False)

            lines_data: List[LineResult] = []
            conf_sum = 0.0

            if hasattr(page, "lines") and page.lines:
                for ln in page.lines:
                    text_str = getattr(ln, "text", "").strip()
                    box = list(getattr(ln, "box", [0, 0, 0, 0]))
                    conf = float(getattr(ln, "conf", 0.0))
                    if text_str:
                        # Precompute character horizontal boundaries
                        bx0, by0, bx1, by1 = box
                        line_w = bx1 - bx0
                        weights = [_char_weight(c) for c in text_str]
                        total_weight = sum(weights) or 1.0

                        cum_w = [0.0]
                        curr = 0.0
                        for w in weights:
                            curr += w
                            cum_w.append(curr / total_weight)

                        char_xs = [bx0 + w * line_w for w in cum_w]

                        lines_data.append(LineResult(
                            text=text_str,
                            box=box,
                            conf=conf,
                            char_xs=char_xs
                        ))
                        conf_sum += conf

            # Reconstruct clean text
            raw_text = getattr(page, "text", "")
            if not raw_text and lines_data:
                raw_text = "\n".join(l.text for l in lines_data)

            raw_text = raw_text.strip()
            markdown_text = getattr(page, "markdown", raw_text).strip()

            words = raw_text.split()
            word_count = len(words)
            line_count = len(lines_data)
            avg_conf = (conf_sum / len(lines_data)) if lines_data else 1.0
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            return OCRResult(
                text=raw_text,
                markdown=markdown_text,
                lines=lines_data,
                word_count=word_count,
                line_count=line_count,
                avg_confidence=avg_conf,
                elapsed_ms=round(elapsed_ms, 1)
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return OCRResult(
                text="",
                markdown="",
                elapsed_ms=round(elapsed_ms, 1),
                error=str(e)
            )

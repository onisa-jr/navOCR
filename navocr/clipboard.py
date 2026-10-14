"""
System clipboard integration for navOcr.
Supports Qt clipboard and X11 xclip for persistent text and image clipboard access.
"""

import subprocess
import shutil
import io
from PIL import Image
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QClipboard, QPixmap, QImage


def copy_to_clipboard(text: str) -> bool:
    """
    Copies text to both QApplication clipboard and X11 xclip (if available),
    ensuring other applications can paste immediately.
    """
    if not text:
        return False

    success = False

    # 1. Qt Clipboard (regular and selection buffer)
    app = QApplication.instance()
    if app:
        clipboard = app.clipboard()
        clipboard.setText(text, QClipboard.Clipboard)
        clipboard.setText(text, QClipboard.Selection)
        success = True

    # 2. X11 xclip fallback / backup for persistence
    if shutil.which("xclip"):
        try:
            p1 = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            p1.communicate(input=text.encode("utf-8"), timeout=1.0)

            p2 = subprocess.Popen(
                ["xclip", "-selection", "primary"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            p2.communicate(input=text.encode("utf-8"), timeout=1.0)
            success = True
        except Exception:
            pass

    return success


def copy_image_to_clipboard(pil_image: Image.Image) -> bool:
    """
    Copies image directly to system clipboard (as PNG/bitmap),
    allowing immediate paste into image editors, chat apps, and documents.
    """
    if pil_image is None:
        return False

    success = False

    # 1. Qt Clipboard image
    app = QApplication.instance()
    if app:
        try:
            if pil_image.mode != "RGBA":
                conv_img = pil_image.convert("RGBA")
            else:
                conv_img = pil_image
            data = conv_img.tobytes("raw", "RGBA")
            q_img = QImage(data, conv_img.width, conv_img.height, QImage.Format_RGBA8888).copy()
            q_pix = QPixmap.fromImage(q_img)

            clipboard = app.clipboard()
            clipboard.setImage(q_img, QClipboard.Clipboard)
            clipboard.setPixmap(q_pix, QClipboard.Clipboard)
            success = True
        except Exception:
            pass

    # 2. X11 xclip with image/png target for persistent pasting
    if shutil.which("xclip"):
        try:
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            png_bytes = buf.getvalue()

            p = subprocess.Popen(
                ["xclip", "-selection", "clipboard", "-target", "image/png"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            p.communicate(input=png_bytes, timeout=1.5)
            success = True
        except Exception:
            pass

    return success

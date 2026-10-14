"""
Compatibility and environment sanity checks for Qt and OpenCV.
Prevents OpenCV's bundled Qt plugins from corrupting the system Qt5 runtime.
"""

import os
import sys

SYSTEM_QT5_PLUGIN_PATHS = [
    "/usr/lib/x86_64-linux-gnu/qt5/plugins",
    "/usr/lib/aarch64-linux-gnu/qt5/plugins",
    "/usr/lib/qt5/plugins",
    "/usr/lib64/qt5/plugins",
]


def ensure_qt_environment():
    """
    Ensures that Qt platform plugin path points to system Qt5 plugins
    and NOT OpenCV's internal broken plugin directory.
    """
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

    for p in SYSTEM_QT5_PLUGIN_PATHS:
        if os.path.exists(os.path.join(p, "platforms", "libqxcb.so")):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = p
            return p

    # Fallback: if QT_QPA_PLATFORM_PLUGIN_PATH points to cv2, remove it
    current = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "")
    if "cv2" in current:
        del os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"]

    return None

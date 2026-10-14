"""
Configuration management for navOcr.
Settings are persisted in ~/.config/navocr/config.json.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "navocr"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    shortcut: str = "<print_screen>"  # PrintScreen key (pynput format)
    shortcut_display: str = "PrintScreen"
    auto_copy: bool = False    # Auto-copy full recognized text on release
    dim_opacity: float = 0.45  # Overlay darkening factor (0.0 - 1.0)
    threads: int = 4           # IndraOCR inference threads
    show_tray_icon: bool = True

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_FILE.exists():
            config = cls()
            config.save()
            return config

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception:
            return cls()

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

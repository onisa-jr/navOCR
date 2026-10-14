"""
NavVide Design System tokens and style definitions for navOcr.
Adheres strictly to the NavVide desktop design specifications:
- Canvas: #0a0f0d
- Panel: #121815
- Card / row hover: #1a221e
- Hairline border: #1c2b22
- Border hover / active: #2e4536
- Text primary: #f2f5f3
- Text secondary: #c7d3cc
- Text tertiary: #8fa398
- Text muted: #5b675f
- Accent (brand + primary action): #4ade80
- Accent text on fill: #06280f
- Status online/normal: #4ade80, degraded: #f2b544, alert: #ef4444
"""

COLOR_CANVAS = "#0a0f0d"
COLOR_PANEL = "#121815"
COLOR_HOVER = "#1a221e"
COLOR_BORDER = "#1c2b22"
COLOR_BORDER_ACTIVE = "#2e4536"

COLOR_TEXT_PRIMARY = "#f2f5f3"
COLOR_TEXT_SECONDARY = "#c7d3cc"
COLOR_TEXT_TERTIARY = "#8fa398"
COLOR_TEXT_MUTED = "#5b675f"

COLOR_ACCENT = "#4ade80"
COLOR_ACCENT_HOVER = "#5eead4"
COLOR_ACCENT_TEXT = "#06280f"

COLOR_STATUS_ONLINE = "#4ade80"
COLOR_STATUS_DEGRADED = "#f2b544"
COLOR_STATUS_ALERT = "#ef4444"

# Optical Neon Illumination Tokens
COLOR_NEON_PRIMARY = "#39ff8a"
COLOR_NEON_GLOW = "#8cffb9"
COLOR_NEON_HIGHLIGHT = "rgba(57, 255, 138, 0.35)"

FONT_FAMILY = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Ubuntu, "Helvetica Neue", sans-serif'
FONT_MONO = '"JetBrains Mono", "Fira Code", monospace, "DejaVu Sans Mono"'

APP_STYLESHEET = f"""
QWidget {{
    background-color: {COLOR_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: 13px;
}}

/* Main Floating Panel Container */
QFrame#mainCard {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}

/* Top Header Bar */
QFrame#headerBar {{
    background-color: {COLOR_PANEL};
    border-bottom: 1px solid {COLOR_BORDER};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

QLabel#appTitle {{
    font-size: 13px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
    letter-spacing: 0.3px;
}}

QLabel#statusBadge {{
    font-size: 11px;
    color: {COLOR_TEXT_TERTIARY};
    background-color: {COLOR_HOVER};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 2px 6px;
}}

QLabel#statPill {{
    font-size: 11px;
    color: {COLOR_STATUS_ONLINE};
    font-weight: 500;
}}

/* Selectable Text View */
QPlainTextEdit#ocrTextView {{
    background-color: #0c120f;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 10px;
    font-size: 13px;
    line-height: 1.45;
    selection-background-color: {COLOR_BORDER_ACTIVE};
    selection-color: {COLOR_ACCENT};
}}

QPlainTextEdit#ocrTextView:focus {{
    border: 1px solid {COLOR_BORDER_ACTIVE};
}}

/* Buttons */
QPushButton {{
    font-size: 12px;
    font-weight: 500;
    border-radius: 5px;
    padding: 6px 12px;
    border: 1px solid {COLOR_BORDER};
    background-color: {COLOR_HOVER};
    color: {COLOR_TEXT_SECONDARY};
}}

QPushButton:hover {{
    background-color: #222d28;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_ACTIVE};
}}

QPushButton:pressed {{
    background-color: #17201b;
}}

QPushButton#primaryAction {{
    background-color: {COLOR_ACCENT};
    color: {COLOR_ACCENT_TEXT};
    border: 1px solid {COLOR_ACCENT};
    font-weight: 600;
}}

QPushButton#primaryAction:hover {{
    background-color: #5ef193;
    border: 1px solid #5ef193;
}}

QPushButton#iconBtn {{
    background-color: transparent;
    border: none;
    color: {COLOR_TEXT_TERTIARY};
    padding: 4px;
    border-radius: 4px;
}}

QPushButton#iconBtn:hover {{
    background-color: {COLOR_HOVER};
    color: {COLOR_TEXT_PRIMARY};
}}

QPushButton#closeBtn {{
    background-color: transparent;
    border: none;
    color: {COLOR_TEXT_MUTED};
    font-size: 14px;
    font-weight: bold;
    border-radius: 4px;
    padding: 2px 6px;
}}

QPushButton#closeBtn:hover {{
    background-color: #2d1818;
    color: #f28787;
}}

/* Scrollbar */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 2px 0 2px 0;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_BORDER_ACTIVE};
    min-height: 20px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Live Text Affordance Button */
QFrame#liveTextAffordance {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}

QFrame#liveTextAffordance:hover {{
    background-color: {COLOR_HOVER};
    border: 1px solid {COLOR_BORDER_ACTIVE};
}}
"""

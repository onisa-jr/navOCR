# navOcr

![](asset/NavOCR.gif)
**navOcr** is a lightweight, native-like screen text OCR utility for Debian Linux powered by the **IndraOCR** engine.

It matches the **Apple Live Text** interaction model: activate with a shortcut, drag a box over your screen, and immediately interact with the captured image where recognized words are directly selectable on the image itself,

---

## The Interaction Model

1. **Capture Screen Region**:

   - Activate via global shortcut (`Super + Shift + T`) or run `navocr capture`.
   - Screen dims with crosshair cursor. Drag over any region and release.
2. **Captured Image as Interface (Live Text)**:

   - The captured screenshot is displayed directly in a compact floating viewer right where you captured it.
   - OCR-detected words are mapped to their exact positions in the screenshot.
   - Hovering over recognized words displays the text cursor (`I-beam`).
   - Drag across words to select a single word, multiple words, full sentences, or paragraphs with a native-style highlight.
   - Double-click to select an individual word.
3. **Minimal Floating Icon Toolbar**:

   - **Camera Icon (📷)**: Copies the captured screenshot directly to the system clipboard as an image (pasteable into chat, documents, image editors).
   - **Copy Text Icon (📄)**: Copies the highlighted words/sentences (or all recognized text if none is selected).
   - **Save Image Icon (💾)**: Saves the captured screenshot to `~/Pictures/Screenshots/`.
   - **Select All Icon (Aa)**: Selects all recognized text across the document.
   - **Close (✕)**: Dismisses the viewer and returns to your previous application.
   - **Interactive Hover**: Hovering over any icon immediately displays the action word (e.g. `Copy Image`, `Copy Text`, `Save Image`) both in a native tooltip and in the status bar!

---

## Installation

```bash
cd /home/onisajr/Documents/navOCR
./install.sh
```

---

## Global Shortcut Configuration

### On Debian MATE Desktop:

1. Open **System** > **Preferences** > **Hardware** > **Keyboard Shortcuts** (or run `mate-keybinding-properties`).
2. Scroll to the bottom and click **Add**.
3. Configure:
   - **Name**: `navOcr Live Text`
   - **Command**: `/home/onisajr/.local/bin/navocr capture`
   - **Shortcut**: `Super + Shift + T`

### On GNOME / KDE / XFCE / i3:

Bind the command `navocr capture` to `Super + Shift + T` in your desktop environment's keyboard shortcuts.

---

## CLI Commands

| Command            | Description                                                                |
| ------------------ | -------------------------------------------------------------------------- |
| `navocr capture` | Snips the screen and displays the captured image with selectable live text |
| `navocr daemon`  | Runs the resident background listener for the global shortcut              |
| `navocr test`    | Runs diagnostic self-test verifying IndraOCR and clipboard                 |
| `navocr config`  | Shows current settings and configuration path                              |

"""
Capture Splash Animation Frame Sequence & Contact Sheet
=======================================================
Renders the animated splash screen at exact timestamps (t=0, 100, 200, 400, 600, 800, 1000, 1200, 1400 ms)
for all enterprise themes (Light, Dark, Classic Navy) and builds contact sheet PNGs.
"""
import os
import sys
from pathlib import Path

# Headless offscreen setup
os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QPoint

from app.ui.splash import SplashScreen
from app.ui.theme import theme_manager
from PIL import Image

def capture_theme_frames(theme_key: str):
    print(f"--- Capturing frames for theme: {theme_key} ---")
    theme_manager.apply_theme(theme_key)
    out_dir = ROOT / "docs" / "splash_frames" / theme_key
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamps = [0, 100, 200, 400, 600, 800, 1000, 1200, 1400]
    frame_paths = []

    for t_ms in timestamps:
        # Create splash instance and manually advance properties to exact timestamp
        splash = SplashScreen(reduce_motion=False)
        splash.show_splash()

        # Calculate property states at t_ms
        # 1. Window opacity & card scale (0-250ms)
        p_win = min(1.0, t_ms / 250.0)
        splash.setWindowOpacity(p_win)
        splash.set_card_scale(0.96 + 0.04 * p_win)

        # 2. Logo & line (150-650ms)
        if t_ms < 150:
            splash.set_logo_scale(0.80)
            splash.set_logo_opacity(0.0)
            splash.set_line_expand(0.0)
        else:
            p_logo = min(1.0, (t_ms - 150) / 500.0)
            splash.set_logo_scale(0.80 + 0.20 * p_logo)
            splash.set_logo_opacity(p_logo)
            splash.set_line_expand(p_logo)

        # 3. Title (350-650ms)
        if t_ms < 350:
            splash.set_title_opacity(0.0)
            splash.set_title_offset(8.0)
        else:
            p_title = min(1.0, (t_ms - 350) / 300.0)
            splash.set_title_opacity(p_title)
            splash.set_title_offset(8.0 * (1.0 - p_title))

        # 4. Brand (470-770ms)
        if t_ms < 470:
            splash.set_brand_opacity(0.0)
            splash.set_brand_offset(8.0)
        else:
            p_brand = min(1.0, (t_ms - 470) / 300.0)
            splash.set_brand_opacity(p_brand)
            splash.set_brand_offset(8.0 * (1.0 - p_brand))

        # 5. Tagline (590-850ms)
        if t_ms < 590:
            splash.set_tagline_opacity(0.0)
            splash.set_tagline_offset(8.0)
        else:
            p_tag = min(1.0, (t_ms - 590) / 260.0)
            splash.set_tagline_opacity(p_tag)
            splash.set_tagline_offset(8.0 * (1.0 - p_tag))

        # 6. Progress and status message
        if t_ms <= 100:
            splash.set_progress_value(5.0)
            splash._status_message = "Starting application..."
        elif t_ms <= 200:
            splash.set_progress_value(10.0)
            splash._status_message = "Loading theme..."
        elif t_ms <= 400:
            splash.set_progress_value(25.0)
            splash._status_message = "Checking database..."
        elif t_ms <= 600:
            splash.set_progress_value(45.0)
            splash._status_message = "Applying updates..."
        elif t_ms <= 800:
            splash.set_progress_value(60.0)
            splash._status_message = "Loading company settings..."
        elif t_ms <= 1000:
            splash.set_progress_value(80.0)
            splash._status_message = "Preparing modules..."
        elif t_ms <= 1200:
            splash.set_progress_value(95.0)
            splash._status_message = "Opening workspace..."
        else:
            # Fade-out / ready
            splash.set_progress_value(100.0)
            splash._status_message = "Ready"
            p_fade = max(0.0, 1.0 - ((t_ms - 1200) / 200.0))
            splash.setWindowOpacity(p_fade)

        # Grab pixmap
        pixmap = splash.grab()
        file_path = out_dir / f"t_{t_ms:04d}ms.png"
        pixmap.save(str(file_path))
        frame_paths.append(file_path)
        print(f"  Captured: {file_path.name}")
        splash.close()

    # Build Contact Sheet (3 columns x 3 rows)
    images = [Image.open(p) for p in frame_paths]
    fw, fh = images[0].size
    thumb_w, thumb_h = fw // 2, fh // 2
    cols, rows = 3, 3
    sheet_w, sheet_h = cols * thumb_w, rows * thumb_h

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (25, 25, 30, 255))
    for idx, img in enumerate(images):
        c = idx % cols
        r = idx // cols
        thumb = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (c * thumb_w, r * thumb_h), thumb)

    sheet_path = out_dir / f"contact_sheet_{theme_key}.png"
    sheet.save(str(sheet_path))
    print(f"  Created contact sheet: {sheet_path}")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    themes = ["professional_light", "professional_dark", "classic_navy"]
    for t in themes:
        capture_theme_frames(t)
    print("\nAll frames and contact sheets generated successfully!")


if __name__ == "__main__":
    main()

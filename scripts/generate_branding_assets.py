"""
BillFlow Suite - Branding Asset Generator
=========================================
Generates:
1. assets/branding/app.ico (multi-resolution 16, 24, 32, 48, 64, 128, 256)
2. assets/branding/wizard.bmp (Inno Setup 164x314 banner)
3. assets/branding/wizard_small.bmp (Inno Setup 55x58 header)
"""
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Try importing PySide6 for SVG rasterization
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtWidgets import QApplication

WORKSPACE = Path(__file__).resolve().parent.parent
BRANDING_DIR = WORKSPACE / "assets" / "branding"
BRANDING_DIR.mkdir(parents=True, exist_ok=True)

SVG_PATH = BRANDING_DIR / "logo.svg"
ICO_PATH = BRANDING_DIR / "app.ico"
WIZARD_BMP_PATH = BRANDING_DIR / "wizard.bmp"
WIZARD_SMALL_BMP_PATH = BRANDING_DIR / "wizard_small.bmp"


def rasterize_svg(svg_path: Path, size: int) -> Image.Image:
    """Rasterize an SVG file to a Pillow RGBA image at a given size."""
    app = QApplication.instance() or QApplication(sys.argv)
    renderer = QSvgRenderer(str(svg_path))
    qimg = QImage(size, size, QImage.Format_ARGB32)
    qimg.fill(Qt.transparent)

    painter = QPainter(qimg)
    renderer.render(painter)
    painter.end()

    # Convert QImage to PIL Image
    qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
    width = qimg.width()
    height = qimg.height()
    ptr = qimg.bits()
    # Read bytes
    raw_bytes = bytes(ptr)
    pil_img = Image.frombytes("RGBA", (width, height), raw_bytes)
    return pil_img


def generate_ico():
    """Generates a crisp multi-resolution .ico from logo.svg containing all standard sizes."""
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img_256 = rasterize_svg(SVG_PATH, 256)
    img_256.save(str(ICO_PATH), format="ICO", sizes=sizes)
    print(f"Generated multi-size icon: {ICO_PATH} ({os.path.getsize(ICO_PATH)} bytes)")


def generate_wizard_bmp():
    """
    Generates WizardImageFile: 164x314 BMP.
    Modern gradient (Deep Navy: #0B192C -> #1E3E62) with logo emblem and brand typography.
    """
    w, h = 164, 314
    img = Image.new("RGB", (w, h), (15, 23, 42))  # Slate 900
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    c_top = (11, 25, 44)       # Deep navy
    c_bottom = (30, 62, 98)    # Slate blue
    for y in range(h):
        ratio = y / h
        r = int(c_top[0] * (1 - ratio) + c_bottom[0] * ratio)
        g = int(c_top[1] * (1 - ratio) + c_bottom[1] * ratio)
        b = int(c_top[2] * (1 - ratio) + c_bottom[2] * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Ambient glow in center
    logo_size = 72
    logo_img = rasterize_svg(SVG_PATH, logo_size)
    logo_x = (w - logo_size) // 2
    logo_y = 48
    img.paste(logo_img, (logo_x, logo_y), logo_img)

    # Text styling using standard system font if available
    font_title = None
    font_sub = None
    font_maker = None
    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 16)
        font_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 10)
        font_maker = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 9)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_maker = ImageFont.load_default()

    # Draw Text
    draw.text((w // 2, 140), "BillFlow Suite", fill=(255, 255, 255), font=font_title, anchor="mm")
    draw.text((w // 2, 160), "B2B Accounting & Billing", fill=(147, 197, 253), font=font_sub, anchor="mm")
    draw.text((w // 2, 175), "GST Compliant", fill=(203, 213, 225), font=font_sub, anchor="mm")

    # Divider line
    draw.line([(24, 210), (w - 24, 210)], fill=(51, 65, 85), width=1)

    # Publisher & Maker details
    draw.text((w // 2, 240), "Binapani Automation", fill=(226, 232, 240), font=font_maker, anchor="mm")
    draw.text((w // 2, 256), "Made by Surjyakamal Saha", fill=(148, 163, 184), font=font_maker, anchor="mm")
    draw.text((w // 2, 280), "Version 1.0.0", fill=(100, 116, 139), font=font_maker, anchor="mm")

    img.save(str(WIZARD_BMP_PATH), format="BMP")
    print(f"Generated wizard banner: {WIZARD_BMP_PATH} ({os.path.getsize(WIZARD_BMP_PATH)} bytes)")


def generate_wizard_small_bmp():
    """
    Generates WizardSmallImageFile: 55x58 BMP.
    Top-right header emblem.
    """
    w, h = 55, 58
    img = Image.new("RGB", (w, h), (15, 23, 42))
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    c_top = (15, 23, 42)
    c_bottom = (30, 58, 138)
    for y in range(h):
        ratio = y / h
        r = int(c_top[0] * (1 - ratio) + c_bottom[0] * ratio)
        g = int(c_top[1] * (1 - ratio) + c_bottom[1] * ratio)
        b = int(c_top[2] * (1 - ratio) + c_bottom[2] * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    logo_size = 42
    logo_img = rasterize_svg(SVG_PATH, logo_size)
    logo_x = (w - logo_size) // 2
    logo_y = (h - logo_size) // 2
    img.paste(logo_img, (logo_x, logo_y), logo_img)

    img.save(str(WIZARD_SMALL_BMP_PATH), format="BMP")
    print(f"Generated wizard small banner: {WIZARD_SMALL_BMP_PATH} ({os.path.getsize(WIZARD_SMALL_BMP_PATH)} bytes)")


if __name__ == "__main__":
    generate_ico()
    generate_wizard_bmp()
    generate_wizard_small_bmp()

"""
BillFlow Suite - Core PDF Layout Engine: Safe Image Loader
==========================================================
Loads logos, company seals, and signatures with safety checks:
- Verifies real image headers (PNG/JPG)
- Never crashes on missing, corrupt, or unreadable files
- Auto-scales within bounding boxes while strictly preserving aspect ratio
- Supports transparent PNGs
"""
import os
import logging
from typing import Optional, Tuple
from pathlib import Path
from reportlab.platypus import Image as RLImage

logger = logging.getLogger("pdf_images")


def _is_valid_image_file(path: str) -> bool:
    """Checks if the path exists, is under 5MB, and has a valid PNG/JPEG header."""
    try:
        p = Path(path)
        if not p.is_file():
            return False
        if p.stat().st_size == 0 or p.stat().st_size > 5 * 1024 * 1024:
            return False
        with open(p, "rb") as f:
            header = f.read(16)
            # PNG header: 89 50 4E 47 0D 0A 1A 0A
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                return True
            # JPEG header: FF D8 FF
            if header.startswith(b"\xff\xd8\xff"):
                return True
            # BMP: BM
            if header.startswith(b"BM"):
                return True
        return False
    except Exception as e:
        logger.warning(f"Error checking image header for {path}: {e}")
        return False


def load_safe_image(
    path: Optional[str],
    max_width: Optional[float] = None,
    max_height: Optional[float] = None,
    max_w: Optional[float] = None,
    max_h: Optional[float] = None,
    max_w_pt: Optional[float] = None,
    max_h_pt: Optional[float] = None,
    kind: str = "image"
) -> Optional[RLImage]:
    """
    Safely loads and scales an image for inclusion in ReportLab flowables.
    Returns None if missing or corrupt, never raising an unhandled exception.
    Accepts max_width/max_height, max_w/max_h, or max_w_pt/max_h_pt interchangeably.
    """
    if not path or not isinstance(path, str) or not path.strip():
        return None

    eff_w = max_width or max_w or max_w_pt or 80.0
    eff_h = max_height or max_h or max_h_pt or 40.0

    path_str = path.strip()
    if not _is_valid_image_file(path_str):
        logger.warning(f"Invalid or missing {kind} at '{path_str}'. Skipping.")
        return None

    try:
        # Load initially with ReportLab Image
        img = RLImage(path_str)
        orig_w = float(img.imageWidth)
        orig_h = float(img.imageHeight)

        if orig_w <= 0 or orig_h <= 0:
            return None

        # Calculate aspect-ratio scale
        scale_w = eff_w / orig_w
        scale_h = eff_h / orig_h
        scale = min(scale_w, scale_h, 1.0)  # Never upscale beyond original

        img.drawWidth = orig_w * scale
        img.drawHeight = orig_h * scale
        return img
    except Exception as e:
        logger.warning(f"Failed to render {kind} '{path_str}': {e}. Skipping safely.")
        return None


# Backward-compatible alias
load_logo_image = load_safe_image

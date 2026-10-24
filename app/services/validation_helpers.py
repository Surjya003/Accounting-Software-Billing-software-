"""
Shared Validation Helpers
Implements centralized, robust data sanitization and validation across BillFlow Suite:
- parse_decimal: Indian comma numbers, currency symbols, NaN/Inf rejection (BUG-29)
- validate_gstin: Indian state codes (01-38, 97; reject 99 for parties), regex, checksum, state matching (BUG-04, BUG-05)
- validate_indian_phone: strict 10-digit mobile with +91/0 stripping (BUG-06, BUG-07)
- normalize_name: whitespace stripping & internal space collapsing (BUG-27)
- enforce_max_length: length guards for text fields (BUG-28)
- validate_and_store_logo: magic byte inspection, 2MB limit, auto-resize, local data copy (BUG-03)
"""
import os
import re
import shutil
from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple, Dict, Any
from PIL import Image

from app.config import DATA_DIR

# Valid Indian GSTIN state codes (01 to 38, and 97 Other Territory)
# 99 is Center jurisdiction / non-resident, invalid for regular parties (BUG-04)
VALID_GSTIN_STATE_CODES = {f"{i:02d}" for i in range(1, 39)} | {"97"}

GSTIN_CODE_POINTS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def parse_decimal(val: Any) -> Decimal:
    """
    Parses a numeric value into Decimal (BUG-29).
    Strips commas, spaces, and the ₹ symbol.
    Rejects empty, letters, NaN, Infinity, and scientific notation.
    Raises user-facing ValueError on invalid syntax.
    """
    if val is None:
        raise ValueError("Numeric value cannot be empty.")

    if isinstance(val, (int, float, Decimal)):
        # Check for NaN / Infinity
        if isinstance(val, float):
            import math
            if math.isnan(val) or math.isinf(val):
                raise ValueError("Invalid numeric value (NaN or Infinity not allowed).")
        return Decimal(str(val))

    s = str(val).strip()
    if not s:
        raise ValueError("Numeric value cannot be empty.")

    # Strip ₹ symbol, commas, and spaces
    s = s.replace("₹", "").replace(",", "").replace(" ", "").strip()
    if not s:
        raise ValueError("Numeric value cannot be empty.")

    # Reject scientific notation (e/E), NaN, Infinity, letters
    if re.search(r"[a-df-zA-DF-Z]", s) or "e" in s.lower():
        raise ValueError(f"Invalid numeric value '{val}'.")

    # Strict regex for digits with optional single leading minus and optional decimal point
    if not re.match(r"^-?\d+(\.\d+)?$", s):
        raise ValueError(f"Invalid numeric value '{val}'.")

    try:
        return Decimal(s)
    except (InvalidOperation, Exception):
        raise ValueError(f"Invalid numeric value '{val}'.")


def calculate_gstin_checksum(gstin_14: str) -> str:
    """Calculates official 15th checksum character per GSTN Luhn-mod-36 algorithm."""
    gstin_14 = gstin_14.strip().upper()
    if len(gstin_14) != 14:
        raise ValueError("Input must be exactly 14 characters long.")

    factor = 1
    total = 0
    mod = len(GSTIN_CODE_POINTS)

    for char in gstin_14:
        digit = GSTIN_CODE_POINTS.find(char)
        if digit < 0:
            raise ValueError(f"Invalid character '{char}' in GSTIN.")
        digit *= factor
        digit = (digit // mod) + (digit % mod)
        total += digit
        factor = 2 if factor == 1 else 1

    rem = total % mod
    check_idx = (mod - rem) % mod
    return GSTIN_CODE_POINTS[check_idx]


def validate_gstin(
    gstin: Optional[str],
    state_code: Optional[str] = None,
    verify_checksum: bool = False
) -> bool:
    """
    Validates Indian 15-character GSTIN structure (BUG-04, BUG-05).
    - Auto-uppercases and trims (BUG-05).
    - Rejects invalid state codes (must be 01 to 38, or 97; rejects 99 for parties).
    - Validates regex ^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$.
    - If state_code is provided, checks that the first 2 digits match the selected state code.
    - If verify_checksum is True, checks 15th checksum character.
    """
    if not gstin or not str(gstin).strip():
        return True  # GSTIN is optional for unregistered parties

    g = str(gstin).strip().upper()
    if not GSTIN_PATTERN.match(g):
        return False

    sc = g[:2]
    if sc not in VALID_GSTIN_STATE_CODES:
        return False

    if state_code:
        expected_sc = str(state_code).strip().zfill(2)
        if sc != expected_sc:
            return False

    if verify_checksum:
        try:
            expected_chk = calculate_gstin_checksum(g[:14])
            if g[14] != expected_chk:
                return False
        except Exception:
            return False

    return True


def validate_indian_phone(phone: Optional[str]) -> Tuple[bool, str]:
    """
    Validates Indian mobile number (BUG-06, BUG-07).
    Must be exactly 10 digits starting with 6 to 9.
    Strips optional +91, 91 (if 12 digits), or 0 (if 11 digits).
    Returns (is_valid, cleaned_10_digit_phone).
    """
    if not phone or not str(phone).strip():
        return True, ""

    cleaned = re.sub(r"[\s\-\(\)\.]", "", str(phone).strip())

    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]

    if not re.match(r"^[6-9]\d{9}$", cleaned):
        return False, cleaned

    return True, cleaned


def normalize_name(name: Optional[str]) -> str:
    """Strips leading/trailing spaces and collapses internal runs of whitespace (BUG-27)."""
    if not name:
        return ""
    return " ".join(str(name).strip().split())


def enforce_max_length(field_name: str, value: Optional[str], max_len: int) -> str:
    """Enforces maximum string length limit in service layer (BUG-28)."""
    if not value:
        return ""
    val_str = str(value)
    if len(val_str) > max_len:
        raise ValueError(
            f"{field_name} exceeds maximum allowed length of {max_len} characters (length: {len(val_str)})."
        )
    return val_str


def validate_and_store_image(file_path: str, name_prefix: str = "company_asset") -> str:
    """
    Validates company graphic asset (logo, seal, signature) and copies it to data/ directory.
    - Checks real magic bytes for PNG or JPEG.
    - Rejects files > 2 MB.
    - Auto-resizes if dimensions exceed 2000 px.
    - Saves into data/<name_prefix>.<ext> and returns the target path.
    """
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        raise ValueError(f"Image file '{file_path}' does not exist.")

    # 1. Size check: 2 MB limit
    size = p.stat().st_size
    if size > 2 * 1024 * 1024:
        raise ValueError(f"Image size ({size} bytes) exceeds maximum allowed size of 2 MB.")

    # 2. Header magic bytes check
    with open(p, "rb") as f:
        header = f.read(16)

    is_png = header.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpeg = header.startswith(b"\xff\xd8\xff")

    if not (is_png or is_jpeg):
        raise ValueError("Invalid logo image format. Only PNG, JPG, and JPEG images are supported.")

    # 3. Pillow open and dimension check / resize
    try:
        with Image.open(p) as img:
            ext = ".png" if is_png else ".jpg"
            target_dir = Path(DATA_DIR)
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f"{name_prefix}{ext}"

            # Auto-resize if dimension > 2000px
            if max(img.width, img.height) > 2000:
                img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                img.save(str(target_path))
            else:
                shutil.copy2(p, target_path)

            return str(target_path)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to process image: {e}")


def validate_and_store_logo(file_path: str) -> str:
    """Validates company logo file and copies it to data/ directory (BUG-03)."""
    return validate_and_store_image(file_path, "company_logo")


def validate_model_dict(model_cls, data: Dict[str, Any], allowed_extras: Optional[set] = None) -> Dict[str, Any]:
    """
    Validates that all keys in data correspond to valid columns on model_cls.
    Raises clean ValueError listing unknown keys if any are present (BUG-04).
    """
    valid_cols = set(model_cls.__table__.columns.keys())
    if allowed_extras:
        valid_cols.update(allowed_extras)

    unknown = [k for k in data.keys() if k not in valid_cols]
    if unknown:
        raise ValueError(
            f"Unknown field(s) for {model_cls.__name__}: {', '.join(sorted(unknown))}. "
            f"Allowed fields are: {', '.join(sorted(valid_cols))}"
        )
    return data


def normalize_tax_rate(item: Dict[str, Any]) -> Decimal:
    """
    BUG-02: Normalizes tax rate from item dict.
    Accepts `gst_rate_pct` or `tax_rate`.
    If neither is present, raises ValueError instead of defaulting to 0% (0% must be explicit).
    Updates item with both keys as Decimal.
    """
    val = None
    if "gst_rate_pct" in item and item["gst_rate_pct"] is not None:
        val = item["gst_rate_pct"]
    elif "tax_rate" in item and item["tax_rate"] is not None:
        val = item["tax_rate"]

    if val is None:
        raise ValueError(
            "Tax rate is missing on item. Either 'gst_rate_pct' or 'tax_rate' must be explicitly provided (0% must be explicit)."
        )

    try:
        rate = Decimal(str(val))
    except Exception as e:
        raise ValueError(f"Invalid tax rate '{val}': {e}")

    if rate < Decimal("0") or rate > Decimal("100"):
        raise ValueError(f"Tax rate must be between 0% and 100%, got {rate}%.")

    item["gst_rate_pct"] = rate
    item["tax_rate"] = rate
    return rate


PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
VEHICLE_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,4}[0-9]{4}$")


def normalize_uppercase_string(val: Optional[str]) -> str:
    """Strips whitespace and converts to uppercase (BUG-03)."""
    if val is None:
        return ""
    return str(val).strip().upper()


def validate_pan(pan: Optional[str]) -> bool:
    """Validates 10-character Indian PAN structure: 5 letters, 4 digits, 1 letter."""
    if not pan or not str(pan).strip():
        return True
    p = str(pan).strip().upper()
    return bool(PAN_PATTERN.match(p))


def validate_ifsc(ifsc: Optional[str]) -> bool:
    """Validates 11-character Indian IFSC structure: 4 letters, 0, 6 alphanumeric."""
    if not ifsc or not str(ifsc).strip():
        return True
    code = str(ifsc).strip().upper()
    return bool(IFSC_PATTERN.match(code))


def validate_vehicle_no(vehicle_no: Optional[str]) -> bool:
    """Validates Indian Vehicle Number structure after stripping spaces and hyphens."""
    if not vehicle_no or not str(vehicle_no).strip():
        return True
    clean = re.sub(r"[\s\-]", "", str(vehicle_no).strip().upper())
    return bool(VEHICLE_PATTERN.match(clean))


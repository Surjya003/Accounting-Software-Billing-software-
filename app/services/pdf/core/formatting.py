"""
BillFlow Suite - Core PDF Layout Engine: Formatting & Localization
==================================================================
Provides Indian and International currency number formatting,
strict DD-MM-YYYY date normalization, and Indian numbering amount-to-words.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Union, Optional


def format_currency(
    val: Union[float, int, Decimal, None],
    format_type: str = "Indian",
    include_symbol: bool = False,
    symbol: str = "Rs. "
) -> str:
    """
    Formats a numeric value into currency string:
    - 'Indian': 2,36,000.00 (Lakhs & Crores grouping)
    - 'International': 236,000.00 (Thousands grouping)
    """
    if val is None:
        val = Decimal("0.00")
    if not isinstance(val, Decimal):
        val = Decimal(str(val))

    is_negative = val < 0
    val_abs = abs(val)
    int_part = int(val_abs)
    paise = int(round((val_abs - int_part) * 100))
    if paise >= 100:
        int_part += 1
        paise = 0

    if format_type == "International":
        formatted_int = f"{int_part:,}"
    else:
        # Indian Grouping: Last 3 digits, then groups of 2 digits
        s = str(int_part)
        if len(s) <= 3:
            formatted_int = s
        else:
            last3 = s[-3:]
            remaining = s[:-3]
            groups = []
            while len(remaining) > 2:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            if remaining:
                groups.insert(0, remaining)
            formatted_int = ",".join(groups) + "," + last3

    formatted = f"{formatted_int}.{paise:02d}"
    if is_negative:
        formatted = f"-{formatted}"
    if include_symbol:
        formatted = f"{symbol}{formatted}"
    return formatted


def format_date_ddmmyyyy(dt: Union[date, datetime, str, None]) -> str:
    """
    Normalizes any date object or date string into standard DD-MM-YYYY.
    """
    if dt is None or dt == "":
        return "-"
    if isinstance(dt, (date, datetime)):
        return dt.strftime("%d-%m-%Y")

    s = str(dt).strip()
    # Try common formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(s.split("T")[0].split(" ")[0], fmt)
            return parsed.strftime("%d-%m-%Y")
        except ValueError:
            pass
    return s


def amount_to_words_inr(val: Union[float, int, Decimal, None]) -> str:
    """
    Converts a monetary total into standard Indian legal currency words:
    e.g., 'Rupees Two Lakh Thirty-Six Thousand and Fifty Paise Only'
    """
    if val is None:
        return "Rupees Zero Only"
    if not isinstance(val, Decimal):
        val = Decimal(str(val))

    val_abs = abs(val)
    rupees = int(val_abs)
    paise = int(round((val_abs - rupees) * 100))
    if paise >= 100:
        rupees += 1
        paise = 0

    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
            "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def _convert_below_thousand(n: int) -> str:
        words = []
        if n >= 100:
            words.append(ones[n // 100] + " Hundred")
            n %= 100
        if n >= 20:
            words.append(tens[n // 10])
            n %= 10
        if n > 0:
            words.append(ones[n])
        return " ".join(words).strip()

    def _convert_indian(n: int) -> str:
        if n == 0:
            return ""
        parts = []
        crore = n // 10000000
        n %= 10000000
        if crore > 0:
            parts.append(_convert_indian(crore) + " Crore")
        lakh = n // 100000
        n %= 100000
        if lakh > 0:
            parts.append(_convert_indian(lakh) + " Lakh")
        thousand = n // 1000
        n %= 1000
        if thousand > 0:
            parts.append(_convert_indian(thousand) + " Thousand")
        if n > 0:
            parts.append(_convert_below_thousand(n))
        return " ".join(parts).strip()

    rup_words = _convert_indian(rupees) if rupees > 0 else "Zero"
    res = f"Rupees {rup_words}"

    if paise > 0:
        p_words = _convert_below_thousand(paise)
        res += f" and {p_words} Paise"

    res += " Only"
    return res


def sanitize_number_format(fmt: Optional[str]) -> str:
    """Returns 'Indian' or 'International'."""
    if not fmt:
        return "Indian"
    s = str(fmt).strip().title()
    return "International" if "Inter" in s else "Indian"


# Compatibility aliases
format_inr = format_currency
num_to_words_inr = amount_to_words_inr

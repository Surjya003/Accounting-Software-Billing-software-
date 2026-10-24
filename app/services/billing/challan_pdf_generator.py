"""
Delivery Challan PDF Generator
Routes to dedicated template app.services.pdf.templates.delivery_challan.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.pdf.templates.delivery_challan import render_delivery_challan_pdf


class ChallanPDFGenerator:
    """
    Professional Delivery Challan PDF Generator.
    Delegates to dedicated delivery_challan.py template conforming to Rule 55 CGST.
    """

    def __init__(self):
        pass

    def generate_challan(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Generate a Delivery Challan PDF filling the full A4 page."""
        if not filename:
            from app.config import EXPORTS_DIR
            safe_num = str(data.get("challan_number") or data.get("invoice_number", "DRAFT")).replace("/", "-").replace("\\", "-")
            filename = os.path.join(str(EXPORTS_DIR), f"challan_{safe_num}.pdf")

        filepath = str(filename)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        return render_delivery_challan_pdf(data, filepath)
"""
Professional Proforma Invoice PDF Generator
Routes to dedicated template app.services.pdf.templates.proforma.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.pdf.templates.proforma import render_proforma_pdf


class ProformaPDFGenerator:
    """
    Professional Proforma Invoice PDF Generator.
    Delegates to dedicated proforma.py template with payment-request architecture.
    """

    def __init__(self):
        pass

    def generate_proforma(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Generate a professional proforma invoice PDF filling the full A4 page."""
        if not filename:
            from app.config import EXPORTS_DIR
            safe_num = str(data.get("invoice_number") or data.get("proforma_number", "DRAFT")).replace("/", "-").replace("\\", "-")
            filename = os.path.join(str(EXPORTS_DIR), f"proforma_{safe_num}.pdf")

        filepath = str(filename)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        return render_proforma_pdf(data, filepath)

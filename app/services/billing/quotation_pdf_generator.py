"""
Quotation PDF Generator
Routes to dedicated template app.services.pdf.templates.quotation.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.pdf.templates.quotation import render_quotation_pdf


class QuotationPDFGenerator:
    """
    Generates high-impact, business-oriented PDF quotations covering the full A4 page.
    Delegates to dedicated quotation.py template.
    """

    def __init__(self):
        pass

    def generate_quotation(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Generate a fully styled, commercial quotation PDF covering full A4 page.
        """
        if not filename:
            from app.config import EXPORTS_DIR
            q_num = str(data.get("invoice_number") or data.get("quotation_number", "DRAFT")).replace("/", "-").replace("\\", "-")
            filename = os.path.join(str(EXPORTS_DIR), f"quotation_{q_num}.pdf")

        filepath = str(filename)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        return render_quotation_pdf(data, filepath)

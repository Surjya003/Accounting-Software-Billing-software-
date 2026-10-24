"""
Returns & Credit / Debit Note PDF Generator
Routes to dedicated templates app.services.pdf.templates.credit_note and debit_note.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.pdf.templates.credit_note import render_credit_note_pdf
from app.services.pdf.templates.debit_note import render_debit_note_pdf


class ReturnPDFGenerator:
    """
    Professional Credit Note & Debit Note PDF Generator.
    Delegates to dedicated credit_note.py and debit_note.py templates.
    """

    def __init__(self):
        pass

    def generate_credit_note(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Generate a Sales Return / Credit Note PDF."""
        if not filename:
            from app.config import EXPORTS_DIR
            safe_num = str(data.get("return_number") or data.get("invoice_number", "CN-DRAFT")).replace("/", "-").replace("\\", "-")
            filename = os.path.join(str(EXPORTS_DIR), f"credit_note_{safe_num}.pdf")

        filepath = str(filename)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        return render_credit_note_pdf(data, filepath)

    def generate_debit_note(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Generate a Purchase Return / Debit Note PDF."""
        if not filename:
            from app.config import EXPORTS_DIR
            safe_num = str(data.get("return_number") or data.get("invoice_number", "DN-DRAFT")).replace("/", "-").replace("\\", "-")
            filename = os.path.join(str(EXPORTS_DIR), f"debit_note_{safe_num}.pdf")

        filepath = str(filename)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        return render_debit_note_pdf(data, filepath)


def generate_credit_note_pdf(data: Dict[str, Any], filename: Optional[str] = None) -> str:
    return ReturnPDFGenerator().generate_credit_note(data, filename=filename)


def generate_debit_note_pdf(data: Dict[str, Any], filename: Optional[str] = None) -> str:
    return ReturnPDFGenerator().generate_debit_note(data, filename=filename)

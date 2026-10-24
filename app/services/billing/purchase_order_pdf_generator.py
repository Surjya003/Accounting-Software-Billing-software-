"""
Purchase Order PDF Generator
Routes to dedicated template app.services.pdf.templates.purchase_order.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.pdf.templates.purchase_order import render_purchase_order_pdf


class PurchaseOrderPDFGenerator:
    """
    Professional Purchase Order PDF Generator.
    Delegates to dedicated purchase_order.py template.
    """

    def __init__(self):
        pass

    def generate_po(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Generate a Purchase Order PDF filling the full A4 page."""
        if not filename:
            from app.config import EXPORTS_DIR
            safe_num = str(data.get("po_number") or data.get("invoice_number", "PO-DRAFT")).replace("/", "-").replace("\\", "-")
            filename = os.path.join(str(EXPORTS_DIR), f"po_{safe_num}.pdf")

        filepath = str(filename)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        return render_purchase_order_pdf(data, filepath)


def generate_po_pdf(po_data: Dict[str, Any], comp_data: Optional[Dict[str, Any]] = None, output_path: Optional[str] = None) -> str:
    """Generate a Purchase Order PDF."""
    generator = PurchaseOrderPDFGenerator()
    if comp_data and "company" not in po_data:
        po_data = dict(po_data)
        po_data["company"] = comp_data
    return generator.generate_po(po_data, filename=output_path)

"""
BillFlow Suite - PDF Document Generation Package
Dedicated, statutory-compliant ReportLab layouts for every billing document type.
"""
from app.services.pdf.core.page import (
    PAGE_WIDTH,
    PAGE_HEIGHT,
    PAGE_MARGIN,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    PAGE_SIZE,
    NumberedCanvas,
    BillFlowDocTemplate,
    SimpleDocTemplate,
)
from app.services.pdf.core.formatting import (
    format_currency,
    format_currency as format_inr,
    amount_to_words_inr,
    amount_to_words_inr as num_to_words_inr,
    format_date_ddmmyyyy,
)
from app.services.pdf.templates.tax_invoice import render_tax_invoice_pdf
from app.services.pdf.templates.proforma import render_proforma_pdf
from app.services.pdf.templates.quotation import render_quotation_pdf
from app.services.pdf.templates.delivery_challan import render_delivery_challan_pdf
from app.services.pdf.templates.credit_note import render_credit_note_pdf
from app.services.pdf.templates.debit_note import render_debit_note_pdf
from app.services.pdf.templates.purchase_order import render_purchase_order_pdf
from app.services.pdf.templates.payment_receipt import render_payment_receipt_pdf

__all__ = [
    "PAGE_WIDTH",
    "PAGE_HEIGHT",
    "PAGE_MARGIN",
    "FRAME_WIDTH",
    "FRAME_HEIGHT",
    "PAGE_SIZE",
    "NumberedCanvas",
    "BillFlowDocTemplate",
    "SimpleDocTemplate",
    "format_currency",
    "format_inr",
    "amount_to_words_inr",
    "num_to_words_inr",
    "format_date_ddmmyyyy",
    "render_tax_invoice_pdf",
    "render_proforma_pdf",
    "render_quotation_pdf",
    "render_delivery_challan_pdf",
    "render_credit_note_pdf",
    "render_debit_note_pdf",
    "render_purchase_order_pdf",
    "render_payment_receipt_pdf",
]

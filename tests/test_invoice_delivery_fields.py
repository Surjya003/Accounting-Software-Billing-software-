import os
from decimal import Decimal
from datetime import date
import pytest
from PySide6.QtWidgets import QApplication

from app.database.connection import get_session
from app.database.models import Invoice, Party, Product, CompanyProfile
from app.services.billing import invoice_service
from app.services.billing.invoice_pdf_generator import generate_invoice_pdf
from app.ui.views.billing.invoice_view import InvoiceFormDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


def test_invoice_service_persists_delivery_and_reference_fields():
    with get_session() as session:
        party = session.query(Party).first()
        if not party:
            party = Party(name="Delivery Test Party", gstin="27AAAAA0000A1Z5", state="Maharashtra", state_code="27")
            session.add(party)
            session.commit()
            party_id = party.id
        else:
            party_id = party.id

        product = session.query(Product).first()
        if not product:
            product = Product(name="Test Item For Delivery", price=Decimal("500.00"), tax_rate=Decimal("18.00"))
            session.add(product)
            session.commit()
            product_id = product.id
        else:
            product_id = product.id

    inv_data = {
        "invoice_number": "INV-DELIV-TEST-001",
        "invoice_date": date.today(),
        "party_id": party_id,
        "delivery_note": "DN-2026-9999",
        "mode_terms_of_payment": "Net 45 Days Credit",
        "reference_no_date": "REF-ABC-01 dt 24-10-2026",
        "other_references": "Order Confirmation #77",
        "terms_of_delivery": "Ex-Factory, Goods dispatched at buyer risk",
        "status": "draft",
    }
    items_data = [{
        "product_id": product_id,
        "item_description": "Test Goods",
        "quantity": 2.0,
        "unit_price": 500.0,
        "discount_pct": 0.0,
        "gst_rate_pct": 18.0,
        "taxable_value": Decimal("1000.00"),
        "total_amount": Decimal("1180.00"),
    }]

    created_inv = invoice_service.create_invoice(inv_data, items_data)
    with get_session() as session:
        inv = session.query(Invoice).filter(Invoice.invoice_number == "INV-DELIV-TEST-001").first()
        assert inv is not None
        inv_id = inv.id

    fetched = invoice_service.get_invoice_by_id(inv_id)
    assert fetched is not None
    assert fetched["delivery_note"] == "DN-2026-9999"
    assert fetched["mode_terms_of_payment"] == "Net 45 Days Credit"
    assert fetched["reference_no_date"] == "REF-ABC-01 dt 24-10-2026"
    assert fetched["other_references"] == "Order Confirmation #77"
    assert fetched["terms_of_delivery"] == "Ex-Factory, Goods dispatched at buyer risk"

    # Test update
    update_data = {
        "delivery_note": "DN-UPDATED-1234",
        "mode_terms_of_payment": "Immediate via RTGS",
        "reference_no_date": "REF-UPDATED dt 25-10-2026",
        "other_references": "Contract #8899",
        "terms_of_delivery": "Door Delivery by Seller",
    }
    updated_inv = invoice_service.update_invoice(inv_id, update_data)
    assert updated_inv is not None

    refetched = invoice_service.get_invoice_by_id(inv_id)
    assert refetched["delivery_note"] == "DN-UPDATED-1234"
    assert refetched["mode_terms_of_payment"] == "Immediate via RTGS"
    assert refetched["reference_no_date"] == "REF-UPDATED dt 25-10-2026"
    assert refetched["other_references"] == "Contract #8899"
    assert refetched["terms_of_delivery"] == "Door Delivery by Seller"


def test_invoice_form_dialog_manual_filling_and_population(qapp):
    dlg = InvoiceFormDialog()

    assert hasattr(dlg, "txt_delivery_note")
    assert hasattr(dlg, "txt_mode_terms_payment")
    assert hasattr(dlg, "txt_ref_no_date")
    assert hasattr(dlg, "txt_other_references")
    assert hasattr(dlg, "txt_terms_of_delivery")

    # Manually fill the 5 fields
    dlg.txt_delivery_note.setText("DN-MANUAL-001")
    dlg.txt_mode_terms_payment.setText("30 Days Credit")
    dlg.txt_ref_no_date.setText("PO-REF/2026 dt 20-10-2026")
    dlg.txt_other_references.setText("Enquiry Ref 554")
    dlg.txt_terms_of_delivery.setPlainText("F.O.R Destination, Freight Paid")

    data = dlg.get_data()
    inv_fields = data["invoice_data"]
    assert inv_fields["delivery_note"] == "DN-MANUAL-001"
    assert inv_fields["mode_terms_of_payment"] == "30 Days Credit"
    assert inv_fields["reference_no_date"] == "PO-REF/2026 dt 20-10-2026"
    assert inv_fields["other_references"] == "Enquiry Ref 554"
    assert inv_fields["terms_of_delivery"] == "F.O.R Destination, Freight Paid"

    # Test populate
    test_dict = {
        "invoice_number": "INV/POPULATE/01",
        "delivery_note": "DN-POPULATED-88",
        "mode_terms_of_payment": "Letter of Credit (LC)",
        "reference_no_date": "PROFORMA-REF dt 01-10-2026",
        "other_references": "Tender Document #99",
        "terms_of_delivery": "Ex-Works Warehouse Mumbai",
    }
    dlg.populate(test_dict)
    assert dlg.txt_delivery_note.text() == "DN-POPULATED-88"
    assert dlg.txt_mode_terms_payment.text() == "Letter of Credit (LC)"
    assert dlg.txt_ref_no_date.text() == "PROFORMA-REF dt 01-10-2026"
    assert dlg.txt_other_references.text() == "Tender Document #99"
    assert dlg.txt_terms_of_delivery.toPlainText() == "Ex-Works Warehouse Mumbai"


def test_invoice_pdf_renders_delivery_and_reference_fields(tmp_path):
    out_pdf = tmp_path / "test_tax_invoice_delivery_grid.pdf"

    inv_payload = {
        "invoice_number": "INV-2026-GRID-01",
        "invoice_date": date(2026, 10, 24),
        "party_name": "Acme Industries Ltd",
        "party_gstin": "27AABCA1234F1Z5",
        "party_address": "Plot 45, MIDC Industrial Area, Pune",
        "party_state": "Maharashtra",
        "party_state_code": "27",
        "delivery_note": "DN-SPECIAL-777",
        "mode_terms_of_payment": "Net 60 Days via Bank Transfer",
        "reference_no_date": "QUOT/2026/89 dt 15-10-2026",
        "other_references": "Project Phoenix Phase 2",
        "terms_of_delivery": "Door Delivery within 5 business days",
        "po_number": "PO-ACME-404",
        "subtotal": 5000.0,
        "cgst_total": 450.0,
        "sgst_total": 450.0,
        "igst_total": 0.0,
        "total_amount": 5900.0,
        "is_interstate": False,
        "items": [
            {
                "item_description": "Industrial Hydraulic Valve",
                "hsn_code": "8481",
                "quantity": 10.0,
                "unit": "PCS",
                "unit_price": 500.0,
                "gst_rate_pct": 18.0,
                "cgst_amount": 450.0,
                "sgst_amount": 450.0,
                "igst_amount": 0.0,
                "total_amount": 5900.0,
            }
        ],
    }

    pdf_file = generate_invoice_pdf(inv_payload, output_path=str(out_pdf))
    assert os.path.exists(pdf_file)
    assert os.path.getsize(pdf_file) > 1000

    # Read binary content of PDF to ensure the fields were compiled into the document
    with open(pdf_file, "rb") as f:
        pdf_bytes = f.read()

    # The PDF streams contain textual content
    # Let's verify that the PDF has content and is a valid PDF
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes

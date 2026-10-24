"""
Unit and Integration Tests for Quotation Engine & Dashboard
Tests CRUD, KPIs, Tax Calculations, Stock Deduction, Invoice Conversion, and PDF Generation.
"""
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.database.connection import init_db, get_session
from app.services.party_service import create_party
from app.services.billing import product_service, quotation_service
from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator


class TestQuotationEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        from app.database.models import Party, Product, Quotation, CompanyProfile
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if comp:
                comp.state_code = "27"
            session.query(Party).filter(Party.name.in_([
                "Quotation Test Customer Ltd", "Delhi Enterprise Solutions"
            ])).delete(synchronize_session=False)
            session.query(Product).filter(Product.name.in_([
                "Industrial Control Panel 100A", "Copper Busbar 50x10mm"
            ])).delete(synchronize_session=False)
            session.commit()
        # Create test customer
        cls.customer = create_party({
            "name": "Quotation Test Customer Ltd",
            "party_type": "Customer",
            "state_code": "27",
            "city": "Mumbai",
            "state": "Maharashtra",
            "gstin": "27AABCS1429B1Z8"
        })
        # Create interstate test customer
        cls.inter_customer = create_party({
            "name": "Delhi Enterprise Solutions",
            "party_type": "Customer",
            "state_code": "07",
            "city": "New Delhi",
            "state": "Delhi",
            "gstin": "07AAACD1234E1Z1"
        })
        # Create test products
        cls.product1 = product_service.create_product({
            "name": "Industrial Control Panel 100A",
            "hsn_code": "8537",
            "price": 25000.00,
            "tax_rate": 18.00,
            "stock_quantity": 20.000,
            "unit": "PCS"
        })
        cls.product2 = product_service.create_product({
            "name": "Copper Busbar 50x10mm",
            "hsn_code": "7407",
            "price": 1200.00,
            "tax_rate": 18.00,
            "stock_quantity": 50.000,
            "unit": "MTR"
        })

    def test_01_create_quotation_intra_state(self):
        """Test creating an intra-state quotation with CGST and SGST calculation."""
        q_data = {
            "party_id": self.customer.id,
            "quotation_date": date.today(),
            "valid_until": date.today() + timedelta(days=30),
            "status": "draft",
            "reference_number": "RFQ-2026-99",
            "notes": "Test quotation notes"
        }
        items_data = [
            {
                "product_id": self.product1.id,
                "item_description": "Industrial Control Panel 100A",
                "hsn_code": "8537",
                "quantity": 2,
                "unit": "PCS",
                "unit_price": 25000.00,
                "discount_pct": 10.0,  # 10% disc: 50000 - 5000 = 45000 taxable
                "gst_rate_pct": 18.0,
            }
        ]

        quote = quotation_service.create_quotation(q_data, items_data)
        self.assertIsNotNone(quote.id)
        self.assertTrue(quote.quotation_number.startswith("QT/"))
        self.assertEqual(quote.subtotal, Decimal("45000.00"))
        # 18% GST split into 9% CGST (4050) and 9% SGST (4050)
        self.assertEqual(quote.cgst_total, Decimal("4050.00"))
        self.assertEqual(quote.sgst_total, Decimal("4050.00"))
        self.assertEqual(quote.igst_total, Decimal("0.00"))
        self.assertEqual(quote.total_amount, Decimal("53100.00"))
        self.assertFalse(quote.is_interstate)
        self.assertEqual(quote.reference_number, "RFQ-2026-99")

    def test_02_create_quotation_inter_state(self):
        """Test creating an inter-state quotation with IGST calculation."""
        q_data = {
            "party_id": self.inter_customer.id,
            "quotation_date": date.today(),
            "status": "sent",
            "reference_number": "DEL-QUOTE-01",
        }
        items_data = [
            {
                "product_id": self.product2.id,
                "item_description": "Copper Busbar 50x10mm",
                "hsn_code": "7407",
                "quantity": 10,
                "unit": "MTR",
                "unit_price": 1000.00,
                "discount_pct": 0,
                "gst_rate_pct": 18.0,
            }
        ]

        quote = quotation_service.create_quotation(q_data, items_data)
        self.assertIsNotNone(quote.id)
        self.assertTrue(quote.is_interstate)
        self.assertEqual(quote.subtotal, Decimal("10000.00"))
        self.assertEqual(quote.cgst_total, Decimal("0.00"))
        self.assertEqual(quote.sgst_total, Decimal("0.00"))
        self.assertEqual(quote.igst_total, Decimal("1800.00"))
        self.assertEqual(quote.total_amount, Decimal("11800.00"))

    def test_03_get_quotation_by_id_and_all(self):
        """Test fetching quotation by ID and listing with filters."""
        all_quotes = quotation_service.get_all_quotations()
        self.assertGreaterEqual(len(all_quotes), 2)

        # Search by customer name
        search_res = quotation_service.get_all_quotations(search="Delhi")
        self.assertGreaterEqual(len(search_res), 1)
        self.assertIn("Delhi Enterprise", search_res[0]["party_name"])

        # Fetch details by ID
        first_id = all_quotes[0]["id"]
        detail = quotation_service.get_quotation_by_id(first_id)
        self.assertIsNotNone(detail)
        self.assertIn("items", detail)
        self.assertGreater(len(detail["items"]), 0)

    def test_04_update_quotation(self):
        """Test updating quotation details and recalculating line items."""
        q_data = {
            "party_id": self.customer.id,
            "quotation_date": date.today(),
            "status": "draft",
        }
        items_data = [
            {
                "item_description": "Initial Item",
                "quantity": 1,
                "unit": "PCS",
                "unit_price": 5000.00,
                "discount_pct": 0,
                "gst_rate_pct": 18.0,
            }
        ]
        quote = quotation_service.create_quotation(q_data, items_data)
        q_id = quote.id

        # Update items
        new_items = [
            {
                "item_description": "Updated Item",
                "quantity": 2,
                "unit": "PCS",
                "unit_price": 6000.00,
                "discount_pct": 0,
                "gst_rate_pct": 18.0,
            }
        ]
        updated = quotation_service.update_quotation(
            q_id,
            {"status": "accepted", "notes": "Approved by client via email"},
            new_items
        )
        self.assertEqual(updated.status, "accepted")
        self.assertEqual(updated.subtotal, Decimal("12000.00"))
        self.assertEqual(updated.tax_amount, Decimal("2160.00"))
        self.assertEqual(updated.total_amount, Decimal("14160.00"))
        self.assertEqual(updated.notes, "Approved by client via email")

    def test_05_quotation_kpis(self):
        """Test calculation of quotation dashboard KPIs."""
        kpis = quotation_service.get_quotation_kpis()
        self.assertIn("total_count", kpis)
        self.assertIn("total_value", kpis)
        self.assertIn("draft_count", kpis)
        self.assertIn("sent_count", kpis)
        self.assertIn("accepted_count", kpis)
        self.assertGreaterEqual(kpis["total_count"], 1)

    def test_06_convert_quotation_to_invoice(self):
        """Test converting a quotation to a Tax Invoice and stock deduction."""
        initial_stock = product_service.get_product_by_id(self.product1.id)["stock_quantity"]

        q_data = {
            "party_id": self.customer.id,
            "quotation_date": date.today(),
            "status": "accepted",
        }
        items_data = [
            {
                "product_id": self.product1.id,
                "item_description": "Industrial Control Panel 100A",
                "quantity": 3,
                "unit": "PCS",
                "unit_price": 25000.00,
                "discount_pct": 0,
                "gst_rate_pct": 18.0,
            }
        ]
        quote = quotation_service.create_quotation(q_data, items_data)
        q_id = quote.id

        # Convert to invoice
        invoice = quotation_service.convert_to_invoice(q_id)
        self.assertIsNotNone(invoice.id)
        self.assertTrue(invoice.invoice_number.startswith("INV/"))
        self.assertEqual(invoice.pi_number, quote.quotation_number)

        # Quotation should now be marked converted
        refreshed_q = quotation_service.get_quotation_by_id(q_id)
        self.assertEqual(refreshed_q["status"], "converted")

        # Inventory stock should have decreased by 3
        new_stock = product_service.get_product_by_id(self.product1.id)["stock_quantity"]
        self.assertEqual(new_stock, initial_stock - 3.0)

    def test_07_pdf_generation(self):
        """Test generating an executive Quotation PDF via QuotationPDFGenerator."""
        from app.services.billing.quotation_pdf_generator import QuotationPDFGenerator
        all_quotes = quotation_service.get_all_quotations()
        first_q = quotation_service.get_quotation_by_id(all_quotes[0]["id"])

        generator = QuotationPDFGenerator()
        pdf_data = {
            "invoice_number": first_q["quotation_number"],
            "date": str(first_q["quotation_date"]),
            "valid_until": str(first_q.get("valid_until", "")),
            "reference_number": "RFQ-TEST-99",
            "tax_mode": "intra_state",
            "company": {
                "name": "Sita Ram & Sons Traders",
                "address": "Shop No. 12, Industrial Area Phase II, MIDC",
                "city": "Mumbai",
                "state": "Maharashtra",
                "state_code": "27",
                "gstin": "27AABCS1429B1Z8",
                "pan": "AABCS1429B",
                "phone": "+91 98200 12345",
                "email": "contact@sitaramtraders.com",
                "bank_name": "State Bank of India",
                "account_no": "381928472910",
                "ifsc": "SBIN0001234",
                "bank_branch": "Fort Mumbai Main Branch",
                "upi_id": "sitaramtraders@sbi"
            },
            "customer": {
                "name": first_q.get("party_name"),
                "address": "Plot 45, MIDC Andheri East, Mumbai",
                "state": "Maharashtra",
                "gstin": "27AABCS1429B1Z8",
                "phone": "9876543210",
                "email": "purchases@customer.com"
            },
            "logistics": {
                "destination": "Mumbai Central",
                "dispatched_through": "Road Express",
                "payment_terms": "100% advance against PI/Quotation"
            },
            "items": [
                {
                    "product_name": "Industrial Control Panel 100A",
                    "description": "Custom powder-coated IP65 enclosure with Siemens switchgear",
                    "hsn_code": "8537",
                    "quantity": 2,
                    "unit": "PCS",
                    "unit_price": 25000.00,
                    "discount_pct": 10.0,
                    "tax_rate": 18,
                    "tax_amount": 8100.00
                }
            ],
            "totals": {
                "taxable_amount": 45000.00,
                "cgst_amount": 4050.00,
                "sgst_amount": 4050.00,
                "igst_amount": 0.00,
                "grand_total": 53100.00
            }
        }
        pdf_path = generator.generate_quotation(pdf_data)
        self.assertTrue(Path(pdf_path).exists())
        self.assertGreater(Path(pdf_path).stat().st_size, 2000)

    def test_08_delete_quotation(self):
        """Test deleting a quotation."""
        q_data = {
            "party_id": self.customer.id,
            "quotation_date": date.today(),
            "status": "draft",
        }
        items_data = [
            {
                "item_description": "To be deleted",
                "quantity": 1,
                "unit": "PCS",
                "unit_price": 100.00,
                "discount_pct": 0,
                "gst_rate_pct": 18.0,
            }
        ]
        quote = quotation_service.create_quotation(q_data, items_data)
        q_id = quote.id

        success = quotation_service.delete_quotation(q_id)
        self.assertTrue(success)
        self.assertIsNone(quotation_service.get_quotation_by_id(q_id))


if __name__ == "__main__":
    unittest.main()

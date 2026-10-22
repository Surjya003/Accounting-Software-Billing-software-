"""
Automated Test Suite for Unified Billing Engine
Tests Products, Invoices, Proformas, Purchase Orders, Challans, and Returns.
"""
import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.database.connection import init_db, get_session
from app.services.party_service import create_party
from app.services.billing.gst_engine import GSTEngine, TransactionType
from app.services.billing import product_service
from app.services.billing import invoice_service
from app.services.billing import proforma_service
from app.services.billing import purchase_order_service
from app.services.billing import challan_service
from app.services.billing import return_service


class TestBillingEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        from app.database.models import CompanyProfile, Party, Product
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if comp:
                comp.state_code = "27"
            session.query(Product).filter(Product.name.in_([
                "Industrial Gear 500", "Copper Cable 100m", "Raw Steel Sheet", "Returned Motor Component"
            ])).delete(synchronize_session=False)
            session.query(Party).filter(Party.name.in_([
                "Billing Test Customer", "Interstate Customer Corp", "Billing Test Supplier"
            ])).delete(synchronize_session=False)
            session.commit()

        cls.customer = create_party({
            "name": "Billing Test Customer",
            "party_type": "Customer",
            "state_code": "27",
            "city": "Mumbai",
            "state": "Maharashtra",
        })
        cls.inter_customer = create_party({
            "name": "Interstate Customer Corp",
            "party_type": "Customer",
            "state_code": "06",
            "city": "Gurugram",
            "state": "Haryana",
        })
        cls.supplier = create_party({
            "name": "Billing Test Supplier",
            "party_type": "Supplier",
            "state_code": "27",
            "city": "Pune",
            "state": "Maharashtra",
        })



    def test_01_product_lifecycle_and_stock(self):
        # Create product
        prod = product_service.create_product({
            "name": "Industrial Gear 500",
            "hsn_code": "8483",
            "category": "Machinery",
            "unit": "PCS",
            "price": 1500.00,
            "purchase_price": 1000.00,
            "tax_rate": 18.00,
            "stock_quantity": 50.000,
            "low_stock_threshold": 10.000,
        })
        self.assertIsNotNone(prod.id)
        self.assertEqual(prod.name, "Industrial Gear 500")

        # Fetch product
        p_dict = product_service.get_product_by_id(prod.id)
        self.assertEqual(p_dict["price"], 1500.00)
        self.assertEqual(p_dict["stock_quantity"], 50.0)

        # Check stock helper
        self.assertTrue(product_service.check_stock(prod.id, 20.0))
        self.assertFalse(product_service.check_stock(prod.id, 100.0))

        # Stock update
        success = product_service.update_stock(prod.id, 10.0, 'sale')
        self.assertTrue(success)
        p_after = product_service.get_product_by_id(prod.id)
        self.assertEqual(p_after["stock_quantity"], 40.0)

    def test_02_gst_engine_line_items(self):
        # Intra-state calculation (CGST + SGST)
        res_intra = GSTEngine.calculate_line_item(
            qty=Decimal("10"),
            rate=Decimal("1000.00"),
            discount_percent=Decimal("10"),
            tax_rate=Decimal("18"),
            transaction_type=TransactionType.INTRA_STATE
        )
        self.assertEqual(res_intra["taxable_value"], Decimal("9000.00"))
        self.assertEqual(res_intra["cgst_amt"], Decimal("810.00"))
        self.assertEqual(res_intra["sgst_amt"], Decimal("810.00"))
        self.assertEqual(res_intra["igst_amt"], Decimal("0.00"))
        self.assertEqual(res_intra["total_amount"], Decimal("10620.00"))

        # Inter-state calculation (IGST)
        res_inter = GSTEngine.calculate_line_item(
            qty=Decimal("5"),
            rate=Decimal("2000.00"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("18"),
            transaction_type=TransactionType.INTER_STATE
        )
        self.assertEqual(res_inter["taxable_value"], Decimal("10000.00"))
        self.assertEqual(res_inter["cgst_amt"], Decimal("0.00"))
        self.assertEqual(res_inter["sgst_amt"], Decimal("0.00"))
        self.assertEqual(res_inter["igst_amt"], Decimal("1800.00"))
        self.assertEqual(res_inter["total_amount"], Decimal("11800.00"))

    def test_03_invoice_creation_and_stock_deduction(self):
        prod = product_service.create_product({
            "name": "Copper Cable 100m",
            "price": 2500.00,
            "tax_rate": 18.00,
            "stock_quantity": 20.000,
        })

        inv = invoice_service.create_invoice(
            {
                "party_id": self.customer.id,
                "invoice_date": date.today(),
                "status": "final",
            },
            [
                {
                    "product_id": prod.id,
                    "item_description": "Copper Cable 100m",
                    "quantity": "2",
                    "unit_price": "2500.00",
                    "discount_pct": "0",
                    "gst_rate_pct": "18",
                }
            ]
        )
        self.assertIsNotNone(inv.id)
        self.assertTrue(inv.invoice_number.startswith("INV/"))
        self.assertEqual(inv.subtotal, Decimal("5000.00"))
        self.assertEqual(inv.total_amount, Decimal("5900.00"))

        # Check that stock was reduced by 2
        p_check = product_service.get_product_by_id(prod.id)
        self.assertEqual(p_check["stock_quantity"], 18.0)

    def test_04_proforma_creation(self):
        pf = proforma_service.create_proforma(
            {
                "party_id": self.customer.id,
                "proforma_date": date.today(),
                "status": "sent",
            },
            [
                {
                    "item_description": "Custom Fabrication Job",
                    "quantity": "1",
                    "unit_price": "15000.00",
                    "discount_pct": "5",
                    "gst_rate_pct": "18",
                }
            ]
        )
        self.assertIsNotNone(pf.id)
        self.assertTrue(pf.proforma_number.startswith("PF/"))
        self.assertEqual(pf.subtotal, Decimal("14250.00"))

    def test_05_purchase_order_and_receive_stock(self):
        prod = product_service.create_product({
            "name": "Raw Steel Sheet",
            "purchase_price": 500.00,
            "tax_rate": 18.00,
            "stock_quantity": 10.000,
        })

        po = purchase_order_service.create_purchase_order(
            {
                "party_id": self.supplier.id,
                "po_date": date.today(),
                "status": "sent",
            },
            [
                {
                    "product_id": prod.id,
                    "item_description": "Raw Steel Sheet",
                    "quantity": "50",
                    "unit_price": "500.00",
                    "tax_rate": "18",
                }
            ]
        )
        self.assertIsNotNone(po.id)
        self.assertTrue(po.po_number.startswith("PO/"))
        self.assertEqual(po.subtotal, Decimal("25000.00"))

        # Mark as received -> stock should increase by 50 (from 10 to 60)
        purchase_order_service.mark_as_received(po.id)
        p_check = product_service.get_product_by_id(prod.id)
        self.assertEqual(p_check["stock_quantity"], 60.0)

    def test_06_delivery_challan_creation(self):
        dc = challan_service.create_challan(
            {
                "party_id": self.customer.id,
                "challan_date": date.today(),
                "transport_details": "Truck MH-12-AB-1234",
            },
            [
                {
                    "item_description": "Delivered Hardware Goods",
                    "quantity": "10",
                    "unit_price": "100.00",
                    "tax_rate": "18",
                }
            ]
        )
        self.assertIsNotNone(dc.id)
        self.assertTrue(dc.challan_number.startswith("DC/"))
        self.assertFalse(dc.is_interstate)
        self.assertEqual(dc.subtotal, Decimal("1000.00"))
        self.assertEqual(dc.cgst_total, Decimal("90.00"))
        self.assertEqual(dc.sgst_total, Decimal("90.00"))
        self.assertEqual(dc.igst_total, Decimal("0.00"))
        self.assertEqual(dc.tax_amount, Decimal("180.00"))
        self.assertEqual(dc.total_amount, Decimal("1180.00"))

    def test_06b_delivery_challan_interstate_and_tax_modes(self):
        # 1. Interstate customer with Auto mode (tax_mode=0) -> should be IGST
        dc_inter = challan_service.create_challan(
            {
                "party_id": self.inter_customer.id,
                "challan_date": date.today(),
                "tax_mode": 0,
            },
            [
                {
                    "item_description": "Interstate Machinery Part",
                    "quantity": "5",
                    "unit_price": "2000.00",
                    "gst_rate_pct": "18",
                }
            ]
        )
        self.assertTrue(dc_inter.is_interstate)
        self.assertEqual(dc_inter.subtotal, Decimal("10000.00"))
        self.assertEqual(dc_inter.cgst_total, Decimal("0.00"))
        self.assertEqual(dc_inter.sgst_total, Decimal("0.00"))
        self.assertEqual(dc_inter.igst_total, Decimal("1800.00"))
        self.assertEqual(dc_inter.total_amount, Decimal("11800.00"))

        # 2. Manual override: Intra customer forced to Inter-State (tax_mode=2)
        dc_manual_inter = challan_service.create_challan(
            {
                "party_id": self.customer.id,
                "challan_date": date.today(),
                "tax_mode": 2,
            },
            [
                {
                    "item_description": "Local Goods Forced Interstate",
                    "quantity": "2",
                    "unit_price": "500.00",
                    "tax_rate": "12",
                }
            ]
        )
        self.assertTrue(dc_manual_inter.is_interstate)
        self.assertEqual(dc_manual_inter.subtotal, Decimal("1000.00"))
        self.assertEqual(dc_manual_inter.cgst_total, Decimal("0.00"))
        self.assertEqual(dc_manual_inter.sgst_total, Decimal("0.00"))
        self.assertEqual(dc_manual_inter.igst_total, Decimal("120.00"))

        # 3. Manual override: Inter customer forced to Intra-State (tax_mode=1)
        dc_manual_intra = challan_service.create_challan(
            {
                "party_id": self.inter_customer.id,
                "challan_date": date.today(),
                "tax_mode": 1,
            },
            [
                {
                    "item_description": "Inter Goods Forced Intrastate",
                    "quantity": "2",
                    "unit_price": "500.00",
                    "tax_rate": "12",
                }
            ]
        )
        self.assertFalse(dc_manual_intra.is_interstate)
        self.assertEqual(dc_manual_intra.cgst_total, Decimal("60.00"))
        self.assertEqual(dc_manual_intra.sgst_total, Decimal("60.00"))
        self.assertEqual(dc_manual_intra.igst_total, Decimal("0.00"))

        # 4. Fetch by ID and verify dict contains both gst_rate_pct and tax_rate
        ch_dict = challan_service.get_challan_by_id(dc_inter.id)
        self.assertIsNotNone(ch_dict)
        self.assertEqual(ch_dict["tax_mode"], 2)
        self.assertEqual(len(ch_dict["items"]), 1)
        item = ch_dict["items"][0]
        self.assertEqual(item["gst_rate_pct"], 18.0)
        self.assertEqual(item["tax_rate"], 18.0)
        self.assertEqual(item["igst_amount"], 1800.0)

        # 5. Update challan items and switch tax_mode to intra
        updated = challan_service.update_challan(
            dc_inter.id,
            {"tax_mode": 1, "status": "received"},
            [
                {
                    "item_description": "Updated Item",
                    "quantity": "10",
                    "unit_price": "100.00",
                    "tax_rate": "18",
                }
            ]
        )
        self.assertFalse(updated.is_interstate)
        self.assertEqual(updated.cgst_total, Decimal("90.00"))
        self.assertEqual(updated.sgst_total, Decimal("90.00"))
        self.assertEqual(updated.igst_total, Decimal("0.00"))
        self.assertEqual(updated.status, "received")

    def test_07_sales_return_and_stock_restoration(self):
        prod = product_service.create_product({
            "name": "Returned Motor Component",
            "price": 3000.00,
            "tax_rate": 18.00,
            "stock_quantity": 5.000,
        })

        sr = return_service.create_sales_return(
            {
                "party_id": self.customer.id,
                "return_date": date.today(),
                "reason": "Defective item",
                "status": "approved",
            },
            [
                {
                    "product_id": prod.id,
                    "item_description": "Returned Motor Component",
                    "quantity": "2",
                    "unit_price": "3000.00",
                    "tax_rate": "18",
                }
            ]
        )
        self.assertIsNotNone(sr.id)
        self.assertTrue(sr.return_number.startswith("SR/"))

        # Since status was 'approved', stock should have been restored by 2 (5 -> 7)
        p_check = product_service.get_product_by_id(prod.id)
        self.assertEqual(p_check["stock_quantity"], 7.0)


if __name__ == "__main__":
    unittest.main()

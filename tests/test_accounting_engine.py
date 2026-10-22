"""
Automated Test Suite for VyaparLedger Pro Accounting Engine
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
from app.database.models import Party, Voucher, VoucherItem, CompanyProfile
from app.services.party_service import (
    create_party, update_party, delete_party, get_party_by_id,
    calculate_party_balance, validate_gstin
)
from app.services.voucher_service import (
    create_voucher, calculate_taxes, generate_voucher_number, get_voucher_by_id
)
from app.services.ledger_service import get_party_ledger_statement
from app.services.report_service import (
    get_outstanding_report, get_day_book, get_trial_balance, get_gst_summary, get_dashboard_kpis
)
from app.services.export_service import (
    export_party_ledger_pdf, export_invoice_pdf, export_party_ledger_excel,
    export_outstanding_excel, export_daybook_excel, export_trial_balance_excel,
    num_to_words_inr
)
from app.services.license_service import (
    get_machine_fingerprint, generate_license_key, verify_license_key, activate_license, get_license_status
)
from app.config import (
    BALANCE_DEBIT, BALANCE_CREDIT, VOUCHER_DEBIT, VOUCHER_CREDIT, VOUCHER_JOURNAL
)

class TestAccountingEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_gstin_validation(self):
        self.assertTrue(validate_gstin("27AABCS1429B1Z8"))
        self.assertTrue(validate_gstin("06AAACJ0123P1Z5"))
        self.assertTrue(validate_gstin(""))  # empty is optional
        self.assertFalse(validate_gstin("INVALID_GSTIN"))
        self.assertFalse(validate_gstin("12345"))

    def test_02_party_creation_and_balance(self):
        party_data = {
            "name": "Test Customer Alpha",
            "party_type": "Customer",
            "gstin": "27AAAAA0000A1Z5",
            "city": "Pune",
            "state": "Maharashtra",
            "state_code": "27",
            "opening_balance": Decimal("50000.00"),
            "opening_balance_type": BALANCE_DEBIT,
            "credit_period_days": 30
        }
        party = create_party(party_data)
        self.assertIsNotNone(party.id)
        self.assertTrue(party.code.startswith("CUST-"))
        
        with get_session() as session:
            bal_amt, bal_type = calculate_party_balance(session, party.id)
            self.assertEqual(bal_amt, Decimal("50000.00"))
            self.assertEqual(bal_type, BALANCE_DEBIT)

    def test_03_tax_calculation_intra_vs_interstate(self):
        items = [
            {
                "item_description": "Steel Rods",
                "quantity": 2.0,
                "unit_price": 10000.0,
                "discount_pct": 0.0,
                "gst_rate_pct": 18.0
            }
        ]
        # Intra-state (27 -> 27): CGST 9% + SGST 9%
        taxable, cgst, sgst, igst, total, processed = calculate_taxes(items, "27", "27")
        self.assertEqual(taxable, Decimal("20000.00"))
        self.assertEqual(cgst, Decimal("1800.00"))
        self.assertEqual(sgst, Decimal("1800.00"))
        self.assertEqual(igst, Decimal("0.00"))
        self.assertEqual(total, Decimal("23600.00"))
        
        # Inter-state (27 -> 06): IGST 18%
        taxable_int, cgst_int, sgst_int, igst_int, total_int, processed_int = calculate_taxes(items, "27", "06")
        self.assertEqual(cgst_int, Decimal("0.00"))
        self.assertEqual(sgst_int, Decimal("0.00"))
        self.assertEqual(igst_int, Decimal("3600.00"))
        self.assertEqual(total_int, Decimal("23600.00"))

    def test_04_voucher_creation_and_running_ledger(self):
        # Create test customer
        cust = create_party({
            "name": "Beta Enterprises",
            "party_type": "Customer",
            "state_code": "27",
            "opening_balance": Decimal("10000.00"),
            "opening_balance_type": BALANCE_DEBIT
        })
        
        today = date.today()
        
        # 1. Debit Voucher (+23,600 Dr) with Product field -> Balance should be 33,600 Dr
        v_debit = create_voucher(
            {
                "voucher_type": VOUCHER_DEBIT,
                "voucher_date": today - timedelta(days=20),
                "party_id": cust.id,
                "product": "TMT Rebars Fe550D",
                "reference_no": "INV-001"
            },
            [
                {
                    "item_description": "TMT Rebars",
                    "quantity": 2.0,
                    "unit_price": 10000.0,
                    "discount_pct": 0.0,
                    "gst_rate_pct": 18.0
                }
            ]
        )
        self.assertEqual(v_debit.total_amount, Decimal("23600.00"))
        self.assertEqual(v_debit.debit_amount, Decimal("23600.00"))
        self.assertEqual(v_debit.credit_amount, Decimal("0.00"))
        self.assertEqual(v_debit.product, "TMT Rebars Fe550D")
        
        # 2. Credit Voucher (-20,000 Cr) -> Balance should be 13,600 Dr
        v_credit = create_voucher({
            "voucher_type": VOUCHER_CREDIT,
            "voucher_date": today - timedelta(days=5),
            "party_id": cust.id,
            "product": "Cheque Payment",
            "reference_no": "UPI-88912",
            "payment_mode": "UPI",
            "total_amount": Decimal("20000.00"),
            "narration": "UPI payment from Beta"
        })
        self.assertEqual(v_credit.credit_amount, Decimal("20000.00"))
        
        # Check Ledger Statement
        statement = get_party_ledger_statement(cust.id, from_date=today - timedelta(days=30), to_date=today)
        self.assertEqual(statement["opening_balance"]["amount"], 10000.00)
        self.assertEqual(statement["opening_balance"]["type"], "Dr")
        self.assertEqual(len(statement["entries"]), 2)
        self.assertEqual(statement["entries"][0]["product"], "TMT Rebars Fe550D")
        self.assertEqual(statement["total_debit"], 23600.00)
        self.assertEqual(statement["total_credit"], 20000.00)
        self.assertEqual(statement["closing_balance"]["amount"], 13600.00)
        self.assertEqual(statement["closing_balance"]["type"], "Dr")

    def test_05_outstanding_ageing_report(self):
        rep = get_outstanding_report("Receivables")
        self.assertIn("grand_total", rep)
        self.assertIn("total_0_30", rep)
        self.assertIn("total_31_60", rep)
        self.assertIn("total_61_90", rep)
        self.assertIn("total_90_plus", rep)
        self.assertTrue(rep["grand_total"] >= 0)

    def test_06_trial_balance_and_daybook(self):
        today = date.today()
        db = get_day_book(today - timedelta(days=120), today)
        self.assertIn("rows", db)
        self.assertIn("total_debit", db)
        self.assertIn("total_credit", db)
        
        tb = get_trial_balance(today - timedelta(days=120), today)
        self.assertIn("rows", tb)
        self.assertIn("total_cl_dr", tb)
        self.assertIn("total_cl_cr", tb)

    def test_07_pdf_and_excel_exports(self):
        cust = create_party({
            "name": "Export Test Party",
            "party_type": "Customer",
            "opening_balance": Decimal("5000.00"),
            "opening_balance_type": "Dr"
        })
        statement = get_party_ledger_statement(cust.id)
        
        # Test PDF Generation
        pdf_path = export_party_ledger_pdf(statement)
        self.assertTrue(pdf_path.exists())
        self.assertTrue(pdf_path.stat().st_size > 1000)
        
        # Test Excel Generation
        xlsx_path = export_party_ledger_excel(statement)
        self.assertTrue(xlsx_path.exists())
        self.assertTrue(xlsx_path.stat().st_size > 1000)

    def test_08_number_to_rupee_words(self):
        self.assertEqual(num_to_words_inr(1500), "INR One Thousand Five Hundred Rupees Only")
        self.assertEqual(num_to_words_inr(125000.50), "INR One Lakh Twenty Five Thousand Rupees and Fifty Paise Only")

    def test_09_offline_licensing(self):
        machine_id = get_machine_fingerprint()
        self.assertTrue(machine_id.startswith("VYAP-"))
        
        company = "Test Trading Company Pvt Ltd"
        key = generate_license_key(machine_id, company, "PERPETUAL")
        self.assertTrue(key.startswith("P-"))
        
        valid, msg, exp = verify_license_key(machine_id, company, key)
        self.assertTrue(valid)
        self.assertIsNone(exp)
        
        # Verify tampering fails
        invalid, _, _ = verify_license_key("VYAP-0000-0000-0000", company, key)
        self.assertFalse(invalid)
        
        # Verify activation
        act_success, act_msg = activate_license(company, key)
        self.assertTrue(act_success)
        
    def test_10_party_deletion_protection_and_deletion(self):
        # 1. Party with transactions cannot be deleted
        party_with_tx = create_party({
            "name": "Protected Party Corp",
            "party_type": "Customer",
            "opening_balance": Decimal("0.00")
        })
        create_voucher({
            "voucher_type": VOUCHER_DEBIT,
            "party_id": party_with_tx.id,
            "total_amount": Decimal("5000.00")
        })
        success, msg = delete_party(party_with_tx.id)
        self.assertFalse(success)
        self.assertIn("cannot be deleted", msg)
        self.assertIn("1 existing transaction", msg)
        self.assertIsNotNone(get_party_by_id(party_with_tx.id))
        
        # 2. Party with zero transactions can be cleanly deleted
        party_empty = create_party({
            "name": "Deletable Party Corp",
            "party_type": "Supplier",
            "opening_balance": Decimal("0.00")
        })
        success_del, msg_del = delete_party(party_empty.id)
        self.assertTrue(success_del)
        self.assertEqual(msg_del, "Party deleted successfully")
        self.assertIsNone(get_party_by_id(party_empty.id))

if __name__ == "__main__":
    unittest.main()

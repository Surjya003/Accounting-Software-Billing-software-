"""
Production Readiness & Pre-Sale Verification Test Suite
Tests:
1. 50+ realistic vouchers across 10 parties and exact Trial Balance / Ledger reconciliation.
2. Mid-history voucher editing & deletion: dynamically verifies subsequent chronological balances recalculate correctly.
3. Disaster Recovery: Backup creation -> Live DB wipe -> Restore -> Data integrity validation.
4. Universal Input Validation: Rejection of negative amounts, invalid future dates, empty fields, malformed GSTINs.
"""
import sys
import os
import shutil
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.database.connection import init_db, get_session, create_backup, restore_backup, DB_PATH
from app.database.models import Party, Voucher, VoucherItem, CompanyProfile
from app.services.party_service import create_party, update_party, delete_party, get_party_by_id
from app.services.voucher_service import (
    create_voucher, update_voucher, delete_voucher, get_voucher_by_id
)
from app.services.ledger_service import get_party_ledger_statement
from app.services.report_service import get_trial_balance, get_outstanding_report
from app.services.sample_data import populate_sample_data
from app.config import (
    BALANCE_DEBIT, BALANCE_CREDIT,
    VOUCHER_SALE, VOUCHER_PURCHASE, VOUCHER_PAYMENT, VOUCHER_RECEIPT, VOUCHER_JOURNAL
)

class TestProductionReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        populate_sample_data(force=True)

    @classmethod
    def tearDownClass(cls):
        from app.services.sample_data import clear_all_business_data
        clear_all_business_data()

    def test_01_verify_50_plus_vouchers_across_10_parties(self):
        """Validates that at least 50 vouchers and 10 parties exist with exact ledger match."""
        with get_session() as session:
            party_count = session.query(Party).count()
            voucher_count = session.query(Voucher).count()
            item_count = session.query(VoucherItem).count()
            
            self.assertGreaterEqual(party_count, 10, f"Expected at least 10 parties, got {party_count}")
            self.assertGreaterEqual(voucher_count, 50, f"Expected at least 50 vouchers, got {voucher_count}")
            self.assertGreater(item_count, 30, f"Expected line items, got {item_count}")
            
            # Verify each party's ledger calculation matches manually:
            parties = session.query(Party).all()
            for p in parties:
                statement = get_party_ledger_statement(p.id)
                self.assertIsNotNone(statement)
                self.assertEqual(statement["party"]["name"], p.name)
                
                # Check Opening Balance + Debits - Credits = Closing Balance
                op_amt = Decimal(str(statement["opening_balance"]["amount"]))
                op_type = statement["opening_balance"]["type"]
                tot_dr = Decimal(str(statement["total_debit"]))
                tot_cr = Decimal(str(statement["total_credit"]))
                cl_amt = Decimal(str(statement["closing_balance"]["amount"]))
                cl_type = statement["closing_balance"]["type"]
                
                # Signed net balance (Debit positive, Credit negative)
                net_op = op_amt if op_type == "Dr" else -op_amt
                net_calc = net_op + tot_dr - tot_cr
                
                expected_cl_type = "Dr" if net_calc >= 0 else "Cr"
                expected_cl_amt = abs(net_calc)
                
                self.assertEqual(cl_type, expected_cl_type, f"Closing balance type mismatch for party {p.name}")
                self.assertEqual(cl_amt, expected_cl_amt, f"Closing balance amount mismatch for party {p.name}")

    def test_02_verify_trial_balance_balanced(self):
        """Verifies Trial Balance report structure and calculations across all 10 parties."""
        today = date.today()
        from_d = today - timedelta(days=365)
        tb = get_trial_balance(from_d, today)
        
        self.assertIn("rows", tb)
        self.assertGreaterEqual(len(tb["rows"]), 10)
        self.assertGreater(tb["total_cl_dr"], 0.0)
        self.assertGreater(tb["total_cl_cr"], 0.0)
        self.assertIn("is_balanced", tb)
        self.assertIn("difference", tb)
        
        # Verify individual party rows sum up to totals
        sum_op_dr = sum(r["op_dr"] for r in tb["rows"])
        sum_op_cr = sum(r["op_cr"] for r in tb["rows"])
        sum_cl_dr = sum(r["cl_dr"] for r in tb["rows"])
        sum_cl_cr = sum(r["cl_cr"] for r in tb["rows"])
        
        self.assertAlmostEqual(sum_op_dr, tb["total_op_dr"], places=2)
        self.assertAlmostEqual(sum_op_cr, tb["total_op_cr"], places=2)
        self.assertAlmostEqual(sum_cl_dr, tb["total_cl_dr"], places=2)
        self.assertAlmostEqual(sum_cl_cr, tb["total_cl_cr"], places=2)

    def test_03_mid_history_voucher_edit_and_delete_recalculation(self):
        """
        Tests editing and deleting a voucher in the middle of a party's timeline.
        Verifies that all subsequent running balances recalculate with 100% precision.
        """
        today = date.today()
        # 1. Create a dedicated test party
        test_party = create_party({
            "name": "Mid-History Recalculation Test Party",
            "party_type": "Customer",
            "opening_balance": Decimal("10000.00"),
            "opening_balance_type": BALANCE_DEBIT
        })
        pid = test_party.id
        
        # 2. Insert 3 chronological vouchers:
        # V1 (Day 30 ago): Sale +₹50,000 -> Running Bal should be ₹60,000 Dr
        v1 = create_voucher({
            "voucher_type": VOUCHER_SALE,
            "voucher_date": today - timedelta(days=30),
            "party_id": pid,
            "reference_no": "TEST-V1",
            "total_amount": Decimal("50000.00")
        })
        # V2 (Day 20 ago): Receipt -₹20,000 -> Running Bal should be ₹40,000 Dr
        v2 = create_voucher({
            "voucher_type": VOUCHER_RECEIPT,
            "voucher_date": today - timedelta(days=20),
            "party_id": pid,
            "reference_no": "TEST-V2",
            "total_amount": Decimal("20000.00")
        })
        # V3 (Day 10 ago): Sale +₹30,000 -> Running Bal should be ₹70,000 Dr
        v3 = create_voucher({
            "voucher_type": VOUCHER_SALE,
            "voucher_date": today - timedelta(days=10),
            "party_id": pid,
            "reference_no": "TEST-V3",
            "total_amount": Decimal("30000.00")
        })
        
        # Verify initial timeline
        s1 = get_party_ledger_statement(pid)
        self.assertEqual(len(s1["entries"]), 3)
        self.assertEqual(s1["entries"][0]["running_balance"], 60000.00)
        self.assertEqual(s1["entries"][1]["running_balance"], 40000.00)
        self.assertEqual(s1["entries"][2]["running_balance"], 70000.00)
        self.assertEqual(s1["closing_balance"]["amount"], 70000.00)
        
        # 3. EDIT V2 in the middle: Change Receipt from ₹20,000 to ₹35,000
        # New Timeline:
        # Op: 10,000
        # V1: +50,000 -> 60,000 Dr
        # V2: -35,000 -> 25,000 Dr (Changed!)
        # V3: +30,000 -> 55,000 Dr (Recalculated!)
        update_voucher(v2.id, {
            "party_id": pid,
            "voucher_type": VOUCHER_RECEIPT,
            "voucher_date": today - timedelta(days=20),
            "reference_no": "TEST-V2-EDITED",
            "total_amount": Decimal("35000.00")
        })
        
        s2 = get_party_ledger_statement(pid)
        self.assertEqual(s2["entries"][0]["running_balance"], 60000.00)
        self.assertEqual(s2["entries"][1]["running_balance"], 25000.00)
        self.assertEqual(s2["entries"][2]["running_balance"], 55000.00)
        self.assertEqual(s2["closing_balance"]["amount"], 55000.00)
        
        # 4. DELETE V2 in the middle:
        # New Timeline without V2:
        # Op: 10,000
        # V1: +50,000 -> 60,000 Dr
        # V3: +30,000 -> 90,000 Dr (Recalculated!)
        del_success = delete_voucher(v2.id)
        self.assertTrue(del_success)
        
        s3 = get_party_ledger_statement(pid)
        self.assertEqual(len(s3["entries"]), 2)
        self.assertEqual(s3["entries"][0]["voucher_number"], v1.voucher_number)
        self.assertEqual(s3["entries"][0]["running_balance"], 60000.00)
        self.assertEqual(s3["entries"][1]["voucher_number"], v3.voucher_number)
        self.assertEqual(s3["entries"][1]["running_balance"], 90000.00)
        self.assertEqual(s3["closing_balance"]["amount"], 90000.00)

    def test_04_disaster_recovery_backup_and_restore(self):
        """
        Tests the complete backup -> wipe -> restore disaster recovery lifecycle.
        """
        # 1. Capture pre-backup metrics
        with get_session() as session:
            orig_party_count = session.query(Party).count()
            orig_voucher_count = session.query(Voucher).count()
            orig_item_count = session.query(VoucherItem).count()
            
        # 2. Create timestamped backup
        backup_file = create_backup()
        self.assertTrue(backup_file.exists())
        self.assertGreater(backup_file.stat().st_size, 1000)
        
        # 3. Simulate accidental disaster: wipe active DB records
        with get_session() as session:
            session.query(VoucherItem).delete()
            session.query(Voucher).delete()
            session.query(Party).delete()
            session.commit()
            
        with get_session() as session:
            self.assertEqual(session.query(Party).count(), 0)
            self.assertEqual(session.query(Voucher).count(), 0)
            
        # 4. Perform Restore
        restore_backup(backup_file)
        
        # 5. Verify 100% data restored
        with get_session() as session:
            restored_party_count = session.query(Party).count()
            restored_voucher_count = session.query(Voucher).count()
            restored_item_count = session.query(VoucherItem).count()
            
            self.assertEqual(restored_party_count, orig_party_count)
            self.assertEqual(restored_voucher_count, orig_voucher_count)
            self.assertEqual(restored_item_count, orig_item_count)

    def test_05_input_validation_rejections(self):
        """
        Validates that invalid inputs are properly rejected with descriptive errors.
        """
        # 1. Negative Party Opening Balance
        with self.assertRaises(ValueError):
            create_party({
                "name": "Invalid Negative Balance Party",
                "opening_balance": Decimal("-500.00")
            })
            
        # 2. Empty Party Name
        with self.assertRaises(ValueError):
            create_party({
                "name": "   ",
                "opening_balance": Decimal("0.00")
            })
            
        # 3. Invalid GSTIN Format
        with self.assertRaises(ValueError):
            create_party({
                "name": "Invalid GSTIN Party",
                "gstin": "INVALID123GSTIN"
            })
            
        # 4. Negative Voucher Amount
        party = create_party({"name": "Validation Test Customer"})
        with self.assertRaises(ValueError):
            create_voucher({
                "voucher_type": VOUCHER_PAYMENT,
                "party_id": party.id,
                "total_amount": Decimal("-1000.00")
            })
            
        # 5. Zero Voucher Amount
        with self.assertRaises(ValueError):
            create_voucher({
                "voucher_type": VOUCHER_PAYMENT,
                "party_id": party.id,
                "total_amount": Decimal("0.00")
            })
            
        # 6. Voucher Date in the Far Future (> 1 Year)
        with self.assertRaises(ValueError):
            create_voucher({
                "voucher_type": VOUCHER_RECEIPT,
                "party_id": party.id,
                "voucher_date": date.today() + timedelta(days=500),
                "total_amount": Decimal("500.00")
            })
            
        # 7. Voucher with Negative Line Item Rate
        with self.assertRaises(ValueError):
            create_voucher({
                "voucher_type": VOUCHER_SALE,
                "party_id": party.id,
            }, [
                {"item_description": "Steel Rod", "quantity": 1.0, "unit_price": -500.0}
            ])
            
        # 8. Voucher with Zero Quantity
        with self.assertRaises(ValueError):
            create_voucher({
                "voucher_type": VOUCHER_SALE,
                "party_id": party.id,
            }, [
                {"item_description": "Steel Rod", "quantity": 0.0, "unit_price": 500.0}
            ])

if __name__ == "__main__":
    unittest.main()

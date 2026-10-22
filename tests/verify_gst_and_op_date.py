"""
GST & Opening Balance Date Verification Script
"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.database.connection import init_db, get_session
from app.database.models import Party, Voucher, VoucherItem, CompanyProfile
from app.services.party_service import create_party
from app.services.voucher_service import create_voucher, get_voucher_by_id
from app.services.report_service import get_gst_summary, get_outstanding_report

def verify_gst_and_op_date():
    init_db()
    today = date.today()
    
    # 1. Setup Company
    with get_session() as session:
        session.query(VoucherItem).delete()
        session.query(Voucher).delete()
        session.query(Party).delete()
        
        comp = session.query(CompanyProfile).first()
        comp.name = "Binapani Automation"
        comp.state_code = "19"
        comp.gstin = "19ABCDE1234F1Z5"
        session.commit()
        
    # 2. Create Parties with opening balance dates
    shree = create_party({
        "name": "Shree Textiles", "party_type": "Customer",
        "gstin": "19AAAAA1111A1Z1", "state_code": "19",
        "opening_balance": Decimal("25000.00"), "opening_balance_type": "Dr",
        "opening_balance_date": today # Opened today (0-30 days)
    })
    
    abb = create_party({
        "name": "ABB Distributors", "party_type": "Supplier",
        "gstin": "19CCCCC3333C1Z3", "state_code": "19",
        "opening_balance": Decimal("40000.00"), "opening_balance_type": "Cr",
        "opening_balance_date": today # Opened today (0-30 days)
    })
    
    ganesh = create_party({
        "name": "Ganesh Rice Mill", "party_type": "Customer",
        "gstin": "19BBBBB2222B1Z2", "state_code": "19",
        "opening_balance": Decimal("0.00"), "opening_balance_type": "Dr",
        "opening_balance_date": today
    })
    
    mitra = create_party({
        "name": "Mitra Traders", "party_type": "Supplier",
        "gstin": "19DDDDD4444D1Z4", "state_code": "19",
        "opening_balance": Decimal("0.00"), "opening_balance_type": "Cr",
        "opening_balance_date": today
    })
    
    # 3. Enter Vouchers with explicit GST line items:
    # V1: Sale to Shree Textiles (Taxable ₹18,500, GST ₹3,330 -> CGST ₹1,665 + SGST ₹1,665, Total ₹21,830)
    v1 = create_voucher({
        "voucher_type": "Sale", "voucher_date": today,
        "party_id": shree.id, "reference_no": "INV-1001", "narration": "Textile fabric sale"
    }, [
        {"item_description": "Cotton Textile Roll", "hsn_sac_code": "5208", "quantity": 10.0, "unit": "MTR", "unit_price": 1850.0, "gst_rate_pct": 18.0}
    ])
    
    # V2: Purchase from ABB (Taxable ₹52,000, GST ₹9,360 -> CGST ₹4,680 + SGST ₹4,680, Total ₹61,360)
    v2 = create_voucher({
        "voucher_type": "Purchase", "voucher_date": today,
        "party_id": abb.id, "reference_no": "PO-2001", "narration": "Electrical switchgear"
    }, [
        {"item_description": "ABB Switchgear 63A", "hsn_sac_code": "8536", "quantity": 4.0, "unit": "PCS", "unit_price": 13000.0, "gst_rate_pct": 18.0}
    ])
    
    # V5: Sale to Ganesh Rice Mill (Taxable ₹9,000, GST ₹1,620 -> CGST ₹810 + SGST ₹810, Total ₹10,620)
    v5 = create_voucher({
        "voucher_type": "Sale", "voucher_date": today,
        "party_id": ganesh.id, "reference_no": "INV-1002", "narration": "Rice mill belt"
    }, [
        {"item_description": "Conveyor Belt 100mm", "hsn_sac_code": "4010", "quantity": 2.0, "unit": "PCS", "unit_price": 4500.0, "gst_rate_pct": 18.0}
    ])
    
    # V6: Purchase from Mitra Traders (Taxable ₹12,000, GST ₹2,160 -> CGST ₹1,080 + SGST ₹1,080, Total ₹14,160)
    v6 = create_voucher({
        "voucher_type": "Purchase", "voucher_date": today,
        "party_id": mitra.id, "reference_no": "PO-2002", "narration": "Industrial grease"
    }, [
        {"item_description": "Industrial Bearing Grease", "hsn_sac_code": "2710", "quantity": 6.0, "unit": "CAN", "unit_price": 2000.0, "gst_rate_pct": 18.0}
    ])
    
    # Verify GST calculations:
    v1_dict = get_voucher_by_id(v1.id)
    v2_dict = get_voucher_by_id(v2.id)
    v5_dict = get_voucher_by_id(v5.id)
    v6_dict = get_voucher_by_id(v6.id)
    
    print(f"V1 (Shree Sale): Taxable={v1_dict['amount_untaxed']}, CGST={v1_dict['cgst_amount']}, SGST={v1_dict['sgst_amount']}, Total Tax={v1_dict['total_tax']}, Grand Total={v1_dict['total_amount']}")
    print(f"V2 (ABB Purchase): Taxable={v2_dict['amount_untaxed']}, CGST={v2_dict['cgst_amount']}, SGST={v2_dict['sgst_amount']}, Total Tax={v2_dict['total_tax']}, Grand Total={v2_dict['total_amount']}")
    print(f"V5 (Ganesh Sale): Taxable={v5_dict['amount_untaxed']}, CGST={v5_dict['cgst_amount']}, SGST={v5_dict['sgst_amount']}, Total Tax={v5_dict['total_tax']}, Grand Total={v5_dict['total_amount']}")
    print(f"V6 (Mitra Purchase): Taxable={v6_dict['amount_untaxed']}, CGST={v6_dict['cgst_amount']}, SGST={v6_dict['sgst_amount']}, Total Tax={v6_dict['total_tax']}, Grand Total={v6_dict['total_amount']}")
    
    # Verify GSTR-1 & GSTR-3B summaries:
    gstr1 = get_gst_summary(today, today, report_type="Sales")
    gstr3b = get_gst_summary(today, today, report_type="Purchases")
    print(f"GSTR-1 Summary (Outward): Taxable={gstr1['total_taxable']}, Total CGST={gstr1['total_cgst']}, Total SGST={gstr1['total_sgst']}, Total Tax={gstr1['total_tax']}")
    print(f"GSTR-3B Summary (Inward): Taxable={gstr3b['total_taxable']}, Total CGST={gstr3b['total_cgst']}, Total SGST={gstr3b['total_sgst']}, Total Tax={gstr3b['total_tax']}")
    
    # Verify Ageing when Opening Balance date is today:
    rec = get_outstanding_report("Receivables", as_of_date=today)
    pay = get_outstanding_report("Payables", as_of_date=today)
    print(f"Receivables Ageing with OpDate=Today: 0-30={rec['total_0_30']}, 90+={rec['total_90_plus']}, GrandTotal={rec['grand_total']}")
    print(f"Payables Ageing with OpDate=Today: 0-30={pay['total_0_30']}, 90+={pay['total_90_plus']}, GrandTotal={pay['grand_total']}")

if __name__ == "__main__":
    verify_gst_and_op_date()

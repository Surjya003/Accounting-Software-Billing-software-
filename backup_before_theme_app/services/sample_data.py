"""
Sample Dataset Generator for Indian B2B Trading Demonstrations
Populates 10 realistic Indian B2B parties and 50+ transactions spanning 120 days.
"""
from datetime import date, timedelta
from decimal import Decimal

from app.database.connection import get_session, init_db
from app.database.models import (
    Party, Voucher, VoucherItem, CompanyProfile,
    Product, Invoice, InvoiceItem,
    ProformaInvoice, ProformaItem,
    Quotation, QuotationItem,
    PurchaseOrder, PurchaseOrderItem,
    DeliveryChallan, ChallanItem,
    SalesReturn, SalesReturnItem,
    PurchaseReturn, PurchaseReturnItem,
    Expense, BankAccount, CashBankTransaction, ActivityLog
)
from app.services.party_service import create_party
from app.services.voucher_service import create_voucher
from app.config import (
    PARTY_TYPE_CUSTOMER, PARTY_TYPE_SUPPLIER, PARTY_TYPE_BOTH,
    BALANCE_DEBIT, BALANCE_CREDIT,
    VOUCHER_DEBIT, VOUCHER_CREDIT, VOUCHER_JOURNAL
)


def clear_all_business_data():
    """
    Completely deletes all dummy/sample business data across all modules:
    Parties, Products, Vouchers, Invoices, Quotations, POs, Challans,
    Returns, Expenses, Cash/Bank transactions, and Bank accounts.
    Resets CompanyProfile to a clean default.
    Preserves default ExpenseCategories and LicenseRecord.
    """
    with get_session() as session:
        # Child line items first to respect foreign key constraints
        session.query(VoucherItem).delete()
        session.query(InvoiceItem).delete()
        session.query(ProformaItem).delete()
        session.query(QuotationItem).delete()
        session.query(PurchaseOrderItem).delete()
        session.query(ChallanItem).delete()
        session.query(SalesReturnItem).delete()
        session.query(PurchaseReturnItem).delete()
        session.query(CashBankTransaction).delete()
        session.query(Expense).delete()

        # Parent transaction headers
        session.query(Voucher).delete()
        session.query(Invoice).delete()
        session.query(ProformaInvoice).delete()
        session.query(Quotation).delete()
        session.query(PurchaseOrder).delete()
        session.query(DeliveryChallan).delete()
        session.query(SalesReturn).delete()
        session.query(PurchaseReturn).delete()

        # Master entities
        session.query(Product).delete()
        session.query(Party).delete()
        session.query(BankAccount).delete()
        session.query(ActivityLog).delete()

        # Reset CompanyProfile to clean state
        comp = session.query(CompanyProfile).first()
        if comp:
            comp.name = "My Business"
            comp.trade_name = None
            comp.gstin = None
            comp.pan = None
            comp.address = None
            comp.city = None
            comp.state = "Maharashtra"
            comp.state_code = "27"
            comp.pincode = None
            comp.phone = None
            comp.email = None
            comp.website = None
            comp.bank_name = None
            comp.bank_account_no = None
            comp.bank_ifsc = None
            comp.bank_branch = None
            comp.upi_id = None
            comp.logo_path = None
        else:
            comp = CompanyProfile(name="My Business", state="Maharashtra", state_code="27")
            session.add(comp)

        session.commit()


def populate_sample_data(force: bool = False):
    """Inserts demo parties and 50+ transactions if DB is empty or force=True."""
    init_db()
    
    with get_session() as session:
        count = session.query(Party).count()
        if count > 0 and not force:
            return  # Already has data
            
    if force:
        clear_all_business_data()
            
    today = date.today()
    
    # 1. Create 10 Realistic Indian B2B Trading Parties
    sample_parties = [
        # Suppliers
        {
            "name": "Tata Steel Distribution Ltd",
            "party_type": PARTY_TYPE_SUPPLIER,
            "code": "SUPP-0001",
            "gstin": "27AAACT2727Q1ZW",
            "pan": "AAACT2727Q",
            "contact_person": "Rajesh Sharma",
            "phone": "+91 98210 44556",
            "email": "sales@tatasteeldist.com",
            "address": "Plot 45, Kalamboli Steel Market",
            "city": "Navi Mumbai",
            "state": "Maharashtra",
            "state_code": "27",
            "pincode": "410218",
            "credit_period_days": 30,
            "opening_balance": Decimal("150000.00"),
            "opening_balance_type": BALANCE_CREDIT,
            "notes": "Main supplier for TMT bars and MS pipes."
        },
        {
            "name": "Jindal Pipes & Tubes Corp",
            "party_type": PARTY_TYPE_SUPPLIER,
            "code": "SUPP-0002",
            "gstin": "06AAACJ0123P1Z5",
            "pan": "AAACJ0123P",
            "contact_person": "Vikas Jindal",
            "phone": "+91 98111 22334",
            "email": "vikas@jindalpipes.in",
            "address": "Sector 25, Industrial Area",
            "city": "Gurugram",
            "state": "Haryana",
            "state_code": "06",
            "credit_period_days": 45,
            "opening_balance": Decimal("85000.00"),
            "opening_balance_type": BALANCE_CREDIT,
            "notes": "Inter-state supplier for seamless pipes (IGST)."
        },
        {
            "name": "UltraTech Building Solutions Ltd",
            "party_type": PARTY_TYPE_SUPPLIER,
            "code": "SUPP-0003",
            "gstin": "27AAACU1234M1Z8",
            "pan": "AAACU1234M",
            "contact_person": "Alok Verma",
            "phone": "+91 98333 11223",
            "email": "orders@ultratechcement.com",
            "address": "Ahura Centre, Mahakali Caves Road",
            "city": "Mumbai",
            "state": "Maharashtra",
            "state_code": "27",
            "pincode": "400093",
            "credit_period_days": 21,
            "opening_balance": Decimal("60000.00"),
            "opening_balance_type": BALANCE_CREDIT,
            "notes": "Direct supplier for OPC 53 Grade and PPC Cement."
        },
        {
            "name": "JSW Coated Products Ltd",
            "party_type": PARTY_TYPE_SUPPLIER,
            "code": "SUPP-0004",
            "gstin": "24AAACJ5566R1ZP",
            "pan": "AAACJ5566R",
            "contact_person": "Hiren Patel",
            "phone": "+91 97240 88990",
            "email": "hiren.patel@jswcoated.com",
            "address": "GIDC Estate, Phase 2",
            "city": "Surat",
            "state": "Gujarat",
            "state_code": "24",
            "credit_period_days": 30,
            "opening_balance": Decimal("110000.00"),
            "opening_balance_type": BALANCE_CREDIT,
            "notes": "Supplier for Galvanized plain and corrugated sheets."
        },

        # Customers
        {
            "name": "Shree Ganesh Hardware & Construction",
            "party_type": PARTY_TYPE_CUSTOMER,
            "code": "CUST-0001",
            "gstin": "27ABCDE1234F1Z5",
            "pan": "ABCDE1234F",
            "contact_person": "Ganesh Patel",
            "phone": "+91 98920 11223",
            "email": "ganesh.patel@gmail.com",
            "address": "Shop 14, Station Road, Thane West",
            "city": "Thane",
            "state": "Maharashtra",
            "state_code": "27",
            "credit_period_days": 30,
            "opening_balance": Decimal("120000.00"),
            "opening_balance_type": BALANCE_DEBIT,
            "notes": "Regular bulk contractor customer."
        },
        {
            "name": "Mehta Building Materials Pvt Ltd",
            "party_type": PARTY_TYPE_CUSTOMER,
            "code": "CUST-0002",
            "gstin": "27XYZPA9876Q1Z2",
            "pan": "XYZPA9876Q",
            "contact_person": "Ashwin Mehta",
            "phone": "+91 98205 99887",
            "email": "accounts@mehtabuilders.com",
            "address": "B-Wing, Trade Center, Andheri East",
            "city": "Mumbai",
            "state": "Maharashtra",
            "state_code": "27",
            "credit_period_days": 45,
            "opening_balance": Decimal("340000.00"),
            "opening_balance_type": BALANCE_DEBIT,
            "notes": "Large real-estate infrastructure contractor."
        },
        {
            "name": "Skyline Developers & Infrastructure",
            "party_type": PARTY_TYPE_CUSTOMER,
            "code": "CUST-0003",
            "gstin": "07AABCS9988K1Z3",
            "pan": "AABCS9988K",
            "contact_person": "Manish Gupta",
            "phone": "+91 98100 77665",
            "email": "mgupta@skylineinfra.in",
            "address": "Connaught Place, Barakhamba Road",
            "city": "New Delhi",
            "state": "Delhi",
            "state_code": "07",
            "credit_period_days": 30,
            "opening_balance": Decimal("95000.00"),
            "opening_balance_type": BALANCE_DEBIT,
            "notes": "Inter-state infrastructure client in NCR."
        },
        {
            "name": "Royal Infra Projects Bangalore",
            "party_type": PARTY_TYPE_CUSTOMER,
            "code": "CUST-0004",
            "gstin": "29AABCR4455N1ZO",
            "pan": "AABCR4455N",
            "contact_person": "Karthik Reddy",
            "phone": "+91 99800 33441",
            "email": "karthik@royalinfra.co",
            "address": "Electronic City Phase 1",
            "city": "Bangalore",
            "state": "Karnataka",
            "state_code": "29",
            "credit_period_days": 60,
            "opening_balance": Decimal("180000.00"),
            "opening_balance_type": BALANCE_DEBIT,
            "notes": "Commercial tech-park contractor in South zone."
        },
        {
            "name": "Jai Hind Fabricators (Unregistered)",
            "party_type": PARTY_TYPE_CUSTOMER,
            "code": "CUST-0005",
            "gstin": "",
            "pan": "",
            "contact_person": "Suresh Sawant",
            "phone": "+91 98690 33445",
            "email": "",
            "address": "Kurla Industrial Estate",
            "city": "Mumbai",
            "state": "Maharashtra",
            "state_code": "27",
            "credit_period_days": 15,
            "opening_balance": Decimal("18500.00"),
            "opening_balance_type": BALANCE_DEBIT,
            "notes": "Cash & local fabrication customer."
        },

        # Both
        {
            "name": "Apex Engineering & Traders",
            "party_type": PARTY_TYPE_BOTH,
            "code": "PTY-0001",
            "gstin": "24AAACA5566K1Z9",
            "pan": "AAACA5566K",
            "contact_person": "Kirit Shah",
            "phone": "+91 97234 55678",
            "email": "kirit@apexengineering.com",
            "address": "GIDC Estate, Phase 3",
            "city": "Ahmedabad",
            "state": "Gujarat",
            "state_code": "24",
            "credit_period_days": 30,
            "opening_balance": Decimal("45000.00"),
            "opening_balance_type": BALANCE_DEBIT,
            "notes": "Both supplies special fittings and buys raw metal."
        }
    ]
    
    created_parties = {}
    for p_dict in sample_parties:
        p_obj = create_party(p_dict)
        created_parties[p_dict["name"]] = p_obj.id

    tata = created_parties["Tata Steel Distribution Ltd"]
    jindal = created_parties["Jindal Pipes & Tubes Corp"]
    ultratech = created_parties["UltraTech Building Solutions Ltd"]
    jsw = created_parties["JSW Coated Products Ltd"]
    ganesh = created_parties["Shree Ganesh Hardware & Construction"]
    mehta = created_parties["Mehta Building Materials Pvt Ltd"]
    skyline = created_parties["Skyline Developers & Infrastructure"]
    royal = created_parties["Royal Infra Projects Bangalore"]
    jaihind = created_parties["Jai Hind Fabricators (Unregistered)"]
    apex = created_parties["Apex Engineering & Traders"]

    # 2. Add 52 realistic transactions spanning the last 120 days
    # (Mix of Sale, Purchase, Receipt, Payment, Journal across all 10 parties)
    
    # --- Month 1: 120 to 90 Days Ago ---
    # 1. Purchase from Tata Steel
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=118),
        "party_id": tata, "reference_no": "TAT/24/1001", "narration": "TMT Rebars Fe550D 10mm & 12mm"
    }, [
        {"item_description": "TMT Bars 10mm Fe550D", "quantity": 4.0, "unit": "TON", "unit_price": 54500.0, "discount_pct": 2.0, "gst_rate_pct": 18.0},
        {"item_description": "TMT Bars 12mm Fe550D", "quantity": 6.0, "unit": "TON", "unit_price": 54000.0, "discount_pct": 2.0, "gst_rate_pct": 18.0}
    ])
    # 2. Payment to Tata Steel
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=115),
        "party_id": tata, "reference_no": "RTGS/SBIN001", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("150000.00"), "narration": "RTGS for opening balance clearance"
    })
    # 3. Sale to Mehta Building Materials
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=112),
        "party_id": mehta, "reference_no": "PO/MBM/101", "narration": "Structural steel for commercial building"
    }, [
        {"item_description": "MS Angle 50x50x6mm", "quantity": 5.0, "unit": "TON", "unit_price": 58000.0, "discount_pct": 1.0, "gst_rate_pct": 18.0},
        {"item_description": "MS Channel 100x50mm", "quantity": 4.0, "unit": "TON", "unit_price": 60500.0, "discount_pct": 1.0, "gst_rate_pct": 18.0}
    ])
    # 4. Receipt from Mehta
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=108),
        "party_id": mehta, "reference_no": "HDFC-CHQ-101", "payment_mode": "Cheque",
        "total_amount": Decimal("200000.00"), "narration": "Part payment against bill PO/MBM/101"
    })
    # 5. Purchase from UltraTech
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=105),
        "party_id": ultratech, "reference_no": "UT/MUM/881", "narration": "OPC 53 Grade Cement 500 Bags"
    }, [
        {"item_description": "UltraTech Cement OPC 53 50kg", "quantity": 500.0, "unit": "BAGS", "unit_price": 380.0, "discount_pct": 3.0, "gst_rate_pct": 28.0}
    ])
    # 6. Payment to UltraTech
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=102),
        "party_id": ultratech, "reference_no": "NEFT/UT/01", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("100000.00"), "narration": "NEFT payment against invoice UT/MUM/881"
    })
    # 7. Sale to Shree Ganesh Hardware
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=100),
        "party_id": ganesh, "reference_no": "SGH/ORD/01", "narration": "Cement & TMT supply"
    }, [
        {"item_description": "UltraTech Cement OPC 53", "quantity": 200.0, "unit": "BAGS", "unit_price": 420.0, "discount_pct": 0.0, "gst_rate_pct": 28.0},
        {"item_description": "TMT Bars 10mm Fe550D", "quantity": 2.0, "unit": "TON", "unit_price": 59000.0, "discount_pct": 0.0, "gst_rate_pct": 18.0}
    ])
    # 8. Receipt from Shree Ganesh
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=96),
        "party_id": ganesh, "reference_no": "UPI/SGH/99", "payment_mode": "UPI",
        "total_amount": Decimal("75000.00"), "narration": "UPI payment by Ganesh Patel"
    })
    # 9. Inter-state Purchase from Jindal Pipes (06)
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=94),
        "party_id": jindal, "reference_no": "JIN/24/09", "narration": "Seamless Pipes GI"
    }, [
        {"item_description": "GI Heavy Class Pipe 2 inch", "quantity": 300.0, "unit": "MTR", "unit_price": 420.0, "discount_pct": 5.0, "gst_rate_pct": 18.0}
    ])
    # 10. Inter-state Sale to Skyline Developers (07)
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=92),
        "party_id": skyline, "reference_no": "SKY/DEL/01", "narration": "Inter-state pipe supply (IGST)"
    }, [
        {"item_description": "GI Heavy Class Pipe 2 inch", "quantity": 150.0, "unit": "MTR", "unit_price": 510.0, "discount_pct": 2.0, "gst_rate_pct": 18.0}
    ])

    # --- Month 2: 90 to 60 Days Ago ---
    # 11. Payment to Jindal Pipes
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=88),
        "party_id": jindal, "reference_no": "RTGS/JIN/01", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("85000.00"), "narration": "Payment for opening balance"
    })
    # 12. Purchase from JSW Coated (24)
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=86),
        "party_id": jsw, "reference_no": "JSW/SUR/112", "narration": "Galvanized Corrugated Sheets"
    }, [
        {"item_description": "GC Sheet 0.50mm x 10ft", "quantity": 200.0, "unit": "PCS", "unit_price": 1250.0, "discount_pct": 4.0, "gst_rate_pct": 18.0}
    ])
    # 13. Sale to Royal Infra Bangalore (29)
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=84),
        "party_id": royal, "reference_no": "BLR/RO/01", "narration": "Tech park roof sheets"
    }, [
        {"item_description": "GC Sheet 0.50mm x 10ft", "quantity": 100.0, "unit": "PCS", "unit_price": 1550.0, "discount_pct": 2.0, "gst_rate_pct": 18.0}
    ])
    # 14. Receipt from Royal Infra
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=80),
        "party_id": royal, "reference_no": "NEFT/ROYAL/01", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("100000.00"), "narration": "NEFT advance on Bangalore project"
    })
    # 15. Sale to Jai Hind Fabricators (Unregistered)
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=78),
        "party_id": jaihind, "reference_no": "CASH/JH/01", "narration": "Local MS pipes for railing"
    }, [
        {"item_description": "MS Square Pipe 25x25mm 16G", "quantity": 50.0, "unit": "PCS", "unit_price": 450.0, "discount_pct": 0.0, "gst_rate_pct": 18.0}
    ])
    # 16. Receipt from Jai Hind (Cash)
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=75),
        "party_id": jaihind, "reference_no": "CASH-REC-01", "payment_mode": "Cash",
        "total_amount": Decimal("20000.00"), "narration": "Cash received at shop counter"
    })
    # 17. Purchase from Apex Engineering (24)
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=72),
        "party_id": apex, "reference_no": "APX/AHM/44", "narration": "Industrial High Pressure Flanges"
    }, [
        {"item_description": "Forged Flange 4 inch ANSI 150", "quantity": 40.0, "unit": "PCS", "unit_price": 1850.0, "discount_pct": 5.0, "gst_rate_pct": 18.0}
    ])
    # 18. Sale to Apex Engineering
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=70),
        "party_id": apex, "reference_no": "INV/APX/01", "narration": "Supply of TMT steel raw material"
    }, [
        {"item_description": "TMT Bars 12mm Fe550D", "quantity": 3.0, "unit": "TON", "unit_price": 59500.0, "discount_pct": 2.0, "gst_rate_pct": 18.0}
    ])
    # 19. Journal adjustment with Apex
    create_voucher({
        "voucher_type": VOUCHER_JOURNAL, "voucher_date": today - timedelta(days=68),
        "party_id": apex, "reference_no": "JRN/APX/SETTLE", "debit_amount": Decimal("0.00"),
        "credit_amount": Decimal("15000.00"), "total_amount": Decimal("15000.00"),
        "narration": "Mutual contra set-off between purchase and sale"
    })
    # 20. Purchase from Tata Steel
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=65),
        "party_id": tata, "reference_no": "TAT/24/2040", "narration": "TMT Rebars Fe550D 16mm & 20mm"
    }, [
        {"item_description": "TMT Bars 16mm Fe550D", "quantity": 5.0, "unit": "TON", "unit_price": 53500.0, "discount_pct": 2.0, "gst_rate_pct": 18.0},
        {"item_description": "TMT Bars 20mm Fe550D", "quantity": 5.0, "unit": "TON", "unit_price": 53000.0, "discount_pct": 2.0, "gst_rate_pct": 18.0}
    ])
    # 21. Payment to Tata Steel
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=62),
        "party_id": tata, "reference_no": "RTGS/SBIN002", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("300000.00"), "narration": "RTGS payment against invoice TAT/24/2040"
    })

    # --- Month 3: 60 to 30 Days Ago ---
    # 22. Sale to Mehta Building Materials
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=58),
        "party_id": mehta, "reference_no": "PO/MBM/202", "narration": "TMT bars for tower foundation"
    }, [
        {"item_description": "TMT Bars 16mm Fe550D", "quantity": 4.0, "unit": "TON", "unit_price": 58500.0, "discount_pct": 1.0, "gst_rate_pct": 18.0},
        {"item_description": "TMT Bars 20mm Fe550D", "quantity": 4.0, "unit": "TON", "unit_price": 58000.0, "discount_pct": 1.0, "gst_rate_pct": 18.0}
    ])
    # 23. Receipt from Mehta
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=55),
        "party_id": mehta, "reference_no": "RTGS/MBM/01", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("350000.00"), "narration": "RTGS payment towards foundation lot"
    })
    # 24. Sale to Shree Ganesh Hardware
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=52),
        "party_id": ganesh, "reference_no": "SGH/ORD/02", "narration": "MS Angles and Channels"
    }, [
        {"item_description": "MS Angle 50x50x6mm", "quantity": 2.0, "unit": "TON", "unit_price": 61000.0, "discount_pct": 0.0, "gst_rate_pct": 18.0}
    ])
    # 25. Receipt from Shree Ganesh
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=48),
        "party_id": ganesh, "reference_no": "CHQ/SGH/104", "payment_mode": "Cheque",
        "total_amount": Decimal("100000.00"), "narration": "Cheque payment on account"
    })
    # 26. Purchase from UltraTech
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=45),
        "party_id": ultratech, "reference_no": "UT/MUM/990", "narration": "PPC Cement 400 Bags"
    }, [
        {"item_description": "UltraTech Super PPC Cement", "quantity": 400.0, "unit": "BAGS", "unit_price": 360.0, "discount_pct": 2.5, "gst_rate_pct": 28.0}
    ])
    # 27. Payment to UltraTech
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=42),
        "party_id": ultratech, "reference_no": "NEFT/UT/02", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("150000.00"), "narration": "Payment for cement consignment"
    })
    # 28. Purchase from JSW Coated
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=40),
        "party_id": jsw, "reference_no": "JSW/SUR/190", "narration": "Color coated roofing sheets"
    }, [
        {"item_description": "Color Coated Sheet Blue 0.50mm", "quantity": 150.0, "unit": "PCS", "unit_price": 1650.0, "discount_pct": 3.0, "gst_rate_pct": 18.0}
    ])
    # 29. Payment to JSW Coated
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=38),
        "party_id": jsw, "reference_no": "RTGS/JSW/01", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("200000.00"), "narration": "RTGS against color coated stock"
    })
    # 30. Sale to Skyline Developers
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=35),
        "party_id": skyline, "reference_no": "SKY/DEL/02", "narration": "Roofing sheets consignment"
    }, [
        {"item_description": "Color Coated Sheet Blue 0.50mm", "quantity": 100.0, "unit": "PCS", "unit_price": 1950.0, "discount_pct": 2.0, "gst_rate_pct": 18.0}
    ])
    # 31. Receipt from Skyline
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=32),
        "party_id": skyline, "reference_no": "NEFT/SKY/01", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("150000.00"), "narration": "NEFT from Skyline Delhi"
    })

    # --- Month 4: 30 to 0 Days Ago ---
    # 32. Purchase from Jindal Pipes
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=28),
        "party_id": jindal, "reference_no": "JIN/24/302", "narration": "MS Seamless Pipes Sch40"
    }, [
        {"item_description": "MS Seamless Pipe 4 inch Sch40", "quantity": 80.0, "unit": "MTR", "unit_price": 980.0, "discount_pct": 5.0, "gst_rate_pct": 18.0}
    ])
    # 33. Sale to Royal Infra Bangalore
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=26),
        "party_id": royal, "reference_no": "BLR/RO/02", "narration": "High pressure pipe supply"
    }, [
        {"item_description": "MS Seamless Pipe 4 inch Sch40", "quantity": 60.0, "unit": "MTR", "unit_price": 1250.0, "discount_pct": 0.0, "gst_rate_pct": 18.0}
    ])
    # 34. Receipt from Royal Infra
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=24),
        "party_id": royal, "reference_no": "RTGS/ROYAL/02", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("80000.00"), "narration": "Part RTGS for seamless pipes"
    })
    # 35. Sale to Jai Hind Fabricators
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=22),
        "party_id": jaihind, "reference_no": "CASH/JH/02", "narration": "MS Angle small lot"
    }, [
        {"item_description": "MS Angle 25x25x3mm", "quantity": 30.0, "unit": "PCS", "unit_price": 320.0, "discount_pct": 0.0, "gst_rate_pct": 18.0}
    ])
    # 36. Receipt from Jai Hind (UPI)
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=20),
        "party_id": jaihind, "reference_no": "UPI/JH/901", "payment_mode": "UPI",
        "total_amount": Decimal("10000.00"), "narration": "UPI payment by Suresh"
    })
    # 37. Purchase from Tata Steel
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=18),
        "party_id": tata, "reference_no": "TAT/24/3110", "narration": "TMT Rebars 8mm & 10mm"
    }, [
        {"item_description": "TMT Bars 8mm Fe550D", "quantity": 3.0, "unit": "TON", "unit_price": 55500.0, "discount_pct": 2.0, "gst_rate_pct": 18.0},
        {"item_description": "TMT Bars 10mm Fe550D", "quantity": 4.0, "unit": "TON", "unit_price": 54500.0, "discount_pct": 2.0, "gst_rate_pct": 18.0}
    ])
    # 38. Payment to Tata Steel
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=16),
        "party_id": tata, "reference_no": "RTGS/SBIN003", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("250000.00"), "narration": "RTGS payment"
    })
    # 39. Sale to Shree Ganesh Hardware
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=14),
        "party_id": ganesh, "reference_no": "SGH/ORD/03", "narration": "TMT 8mm lot for house slab"
    }, [
        {"item_description": "TMT Bars 8mm Fe550D", "quantity": 2.5, "unit": "TON", "unit_price": 60500.0, "discount_pct": 0.0, "gst_rate_pct": 18.0}
    ])
    # 40. Receipt from Shree Ganesh
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=12),
        "party_id": ganesh, "reference_no": "UPI/SGH/103", "payment_mode": "UPI",
        "total_amount": Decimal("100000.00"), "narration": "UPI payment towards 8mm lot"
    })
    # 41. Purchase from UltraTech
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=11),
        "party_id": ultratech, "reference_no": "UT/MUM/1040", "narration": "OPC 53 Cement fresh stock"
    }, [
        {"item_description": "UltraTech Cement OPC 53 50kg", "quantity": 300.0, "unit": "BAGS", "unit_price": 385.0, "discount_pct": 2.0, "gst_rate_pct": 28.0}
    ])
    # 42. Sale to Mehta Building Materials
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=10),
        "party_id": mehta, "reference_no": "PO/MBM/303", "narration": "Cement & TMT combined lot"
    }, [
        {"item_description": "UltraTech Cement OPC 53 50kg", "quantity": 200.0, "unit": "BAGS", "unit_price": 430.0, "discount_pct": 1.0, "gst_rate_pct": 28.0},
        {"item_description": "TMT Bars 10mm Fe550D", "quantity": 3.0, "unit": "TON", "unit_price": 59000.0, "discount_pct": 1.0, "gst_rate_pct": 18.0}
    ])
    # 43. Receipt from Mehta
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=8),
        "party_id": mehta, "reference_no": "HDFC-CHQ-202", "payment_mode": "Cheque",
        "total_amount": Decimal("250000.00"), "narration": "Cheque received"
    })
    # 44. Purchase from Apex Engineering
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=7),
        "party_id": apex, "reference_no": "APX/AHM/99", "narration": "Pipe fittings & reducers"
    }, [
        {"item_description": "Concentric Reducer 4x2 inch", "quantity": 50.0, "unit": "PCS", "unit_price": 650.0, "discount_pct": 5.0, "gst_rate_pct": 18.0}
    ])
    # 45. Sale to Apex Engineering
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=6),
        "party_id": apex, "reference_no": "INV/APX/02", "narration": "Raw steel billets"
    }, [
        {"item_description": "MS Square Pipe 25x25mm 16G", "quantity": 60.0, "unit": "PCS", "unit_price": 490.0, "discount_pct": 0.0, "gst_rate_pct": 18.0}
    ])
    # 46. Payment to Apex Engineering
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=5),
        "party_id": apex, "reference_no": "NEFT/APX/01", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("25000.00"), "narration": "NEFT settlement"
    })
    # 47. Sale to Skyline Developers
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=4),
        "party_id": skyline, "reference_no": "SKY/DEL/03", "narration": "TMT Rebars for bridge pillar"
    }, [
        {"item_description": "TMT Bars 20mm Fe550D", "quantity": 3.0, "unit": "TON", "unit_price": 60000.0, "discount_pct": 2.0, "gst_rate_pct": 18.0}
    ])
    # 48. Receipt from Skyline
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today - timedelta(days=3),
        "party_id": skyline, "reference_no": "RTGS/SKY/02", "payment_mode": "Bank Transfer (NEFT/RTGS/IMPS)",
        "total_amount": Decimal("100000.00"), "narration": "Part RTGS"
    })
    # 49. Sale to Royal Infra Bangalore
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today - timedelta(days=2),
        "party_id": royal, "reference_no": "BLR/RO/03", "narration": "Structural steel beams"
    }, [
        {"item_description": "MS Channel 100x50mm", "quantity": 3.0, "unit": "TON", "unit_price": 62000.0, "discount_pct": 1.5, "gst_rate_pct": 18.0}
    ])
    # 50. Discount / Rebate Journal to Mehta
    create_voucher({
        "voucher_type": VOUCHER_JOURNAL, "voucher_date": today - timedelta(days=1),
        "party_id": mehta, "reference_no": "JRN/DISC/02", "debit_amount": Decimal("0.00"),
        "credit_amount": Decimal("8500.00"), "total_amount": Decimal("8500.00"),
        "narration": "Annual turnover incentive / early settlement rebate"
    })
    # 51. Cash Counter Sale Today to Jai Hind
    create_voucher({
        "voucher_type": VOUCHER_DEBIT, "voucher_date": today,
        "party_id": jaihind, "reference_no": "CASH-TODAY-01", "narration": "Immediate cash sale"
    }, [
        {"item_description": "MS Square Pipe 25x25mm 16G", "quantity": 20.0, "unit": "PCS", "unit_price": 460.0, "discount_pct": 0.0, "gst_rate_pct": 18.0}
    ])
    # 52. Receipt Today from Jai Hind
    create_voucher({
        "voucher_type": VOUCHER_CREDIT, "voucher_date": today,
        "party_id": jaihind, "reference_no": "UPI-TODAY-01", "payment_mode": "UPI",
        "total_amount": Decimal("10000.00"), "narration": "UPI payment at delivery"
    })

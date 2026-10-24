import sqlite3
from decimal import Decimal

con = sqlite3.connect("data/test_accounting.db")
cur = con.cursor()

cur.execute("""
    SELECT id, voucher_number, voucher_type, party_id, payment_mode, 
           debit_amount, credit_amount, amount_untaxed, cgst_amount, 
           sgst_amount, igst_amount, total_tax, total_amount, 
           is_tax_invoice, narration, reference_no 
    FROM vouchers
""")
vouchers = cur.fetchall()

print(f"Total vouchers: {len(vouchers)}")
one_sided = []
for v in vouchers:
    vid, num, vtype, pid, pmode, dr, cr, untaxed, cgst, sgst, igst, tax, total, is_inv, narr, ref = v
    dr = Decimal(str(dr or 0))
    cr = Decimal(str(cr or 0))
    untaxed = Decimal(str(untaxed or 0))
    cgst = Decimal(str(cgst or 0))
    sgst = Decimal(str(sgst or 0))
    igst = Decimal(str(igst or 0))
    total = Decimal(str(total or 0))
    
    # Check what kind of voucher this is
    # Sale
    if is_inv or num.startswith("INV"):
        # Dr Party = total
        # Cr Sales = untaxed, Cr CGST = cgst, Cr SGST = sgst, Cr IGST = igst
        # Cr Roundoff = total - (untaxed + cgst + sgst + igst)
        diff = total - (untaxed + cgst + sgst + igst)
        # Dr Party (total) == Cr (untaxed + cgst + sgst + igst + diff)
    elif num.startswith("PUR"):
        # Cr Party = total
        # Dr Purchases = untaxed, Dr Tax = tax
        pass
    elif num.startswith("CN") or (narr and "Credit Note" in narr):
        # Cr Party = total
        # Dr Sales Return = untaxed, Dr Tax = tax
        pass
    elif num.startswith("DN") or (narr and "Debit Note" in narr):
        # Dr Party = total
        # Cr Purchase Return = untaxed, Cr Tax = tax
        pass
    elif vtype == "Debit":
        # Dr Party = dr (payment or debit)
        # Cr Bank / Cash = dr
        pass
    elif vtype == "Credit":
        # Cr Party = cr (receipt or credit)
        # Dr Bank / Cash = cr
        pass
    print(f"Voucher {num} ({vtype}): dr={dr}, cr={cr}, untaxed={untaxed}, total={total}, narr={narr}")

con.close()

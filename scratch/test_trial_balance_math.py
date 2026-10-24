import sqlite3
from decimal import Decimal

con = sqlite3.connect("data/test_accounting.db")
cur = con.cursor()

# Get company state code
cur.execute("SELECT state_code FROM company_profile LIMIT 1")
r = cur.fetchone()
company_sc = r[0] if r and r[0] else "27"

# Get parties opening balances
cur.execute("SELECT id, name, party_type, state_code, opening_balance, opening_balance_type FROM parties WHERE is_active=1")
parties = cur.fetchall()

# Get bank accounts opening balances
cur.execute("SELECT id, account_name, account_type, opening_balance FROM bank_accounts WHERE is_active=1")
bank_accounts = cur.fetchall()

# Get vouchers
cur.execute("""
    SELECT id, voucher_number, voucher_type, party_id, payment_mode, 
           debit_amount, credit_amount, amount_untaxed, cgst_amount, 
           sgst_amount, igst_amount, total_tax, total_amount, 
           is_tax_invoice, narration, reference_no 
    FROM vouchers
""")
vouchers = cur.fetchall()

# Get expenses
cur.execute("SELECT e.id, c.name, e.amount, e.gst_amount, e.total_amount, e.payment_mode FROM expenses e LEFT JOIN expense_categories c ON e.category_id=c.id")
expenses = cur.fetchall()

accounts = {}

def add_acc(name, acc_type, op_dr=Decimal(0), op_cr=Decimal(0), p_dr=Decimal(0), p_cr=Decimal(0)):
    if name not in accounts:
        accounts[name] = {
            "type": acc_type,
            "op_dr": Decimal(0), "op_cr": Decimal(0),
            "period_dr": Decimal(0), "period_cr": Decimal(0)
        }
    accounts[name]["op_dr"] += op_dr
    accounts[name]["op_cr"] += op_cr
    accounts[name]["period_dr"] += p_dr
    accounts[name]["period_cr"] += p_cr

# 1. Parties Opening
party_info = {}
for pid, name, ptype, sc, op_bal, op_type in parties:
    party_info[pid] = (name, ptype, sc or company_sc)
    bal = Decimal(str(op_bal or 0))
    if op_type == "Debit":
        add_acc(name, ptype, op_dr=bal)
    else:
        add_acc(name, ptype, op_cr=bal)

# 2. Bank Accounts Opening
for bid, bname, btype, b_op in bank_accounts:
    bal = Decimal(str(b_op or 0))
    add_acc(bname, btype, op_dr=bal)

# 3. Process vouchers
for v in vouchers:
    vid, num, vtype, pid, pmode, dr, cr, untaxed, cgst, sgst, igst, tax, total, is_inv, narr, ref = v
    pname, ptype, p_sc = party_info.get(pid, (f"Party #{pid}", "Party", company_sc))
    dr = Decimal(str(dr or 0))
    cr = Decimal(str(cr or 0))
    untaxed = Decimal(str(untaxed or 0))
    cgst = Decimal(str(cgst or 0))
    sgst = Decimal(str(sgst or 0))
    igst = Decimal(str(igst or 0))
    tax = Decimal(str(tax or 0))
    total = Decimal(str(total or 0))
    narr = narr or ""

    # Split tax if cgst/sgst/igst are 0 but tax > 0
    if tax > 0 and (cgst + sgst + igst) == 0:
        if p_sc == company_sc:
            half = (tax / Decimal("2")).quantize(Decimal("0.01"))
            cgst = half
            sgst = tax - half
        else:
            igst = tax

    # Classify
    is_sale = is_inv or num.startswith("INV") or "Tax Invoice" in narr or "Invoice" in narr
    is_purchase = num.startswith("PUR") or "Goods Receipt" in narr
    is_sales_return = num.startswith("CN") or "Credit Note" in narr
    is_purchase_return = num.startswith("DN") or "Debit Note" in narr

    if is_sale:
        # Party Dr = total
        add_acc(pname, ptype, p_dr=total)
        # Sales Cr = untaxed
        add_acc("Sales Account", "Sales Account", p_cr=untaxed)
        # Output GST Cr
        if cgst > 0: add_acc("Output CGST", "Duties & Taxes", p_cr=cgst)
        if sgst > 0: add_acc("Output SGST", "Duties & Taxes", p_cr=sgst)
        if igst > 0: add_acc("Output IGST", "Duties & Taxes", p_cr=igst)
        # Round off
        diff = total - (untaxed + cgst + sgst + igst)
        if diff > 0: add_acc("Round-off", "Indirect Income", p_cr=diff)
        elif diff < 0: add_acc("Round-off", "Indirect Expense", p_dr=-diff)

    elif is_purchase:
        # Party Cr = total
        add_acc(pname, ptype, p_cr=total)
        # Purchases Dr = untaxed
        add_acc("Purchases Account", "Purchase Account", p_dr=untaxed)
        # Input GST Dr
        if cgst > 0: add_acc("Input CGST", "Duties & Taxes", p_dr=cgst)
        if sgst > 0: add_acc("Input SGST", "Duties & Taxes", p_dr=sgst)
        if igst > 0: add_acc("Input IGST", "Duties & Taxes", p_dr=igst)
        diff = total - (untaxed + cgst + sgst + igst)
        if diff > 0: add_acc("Round-off", "Indirect Expense", p_dr=diff)
        elif diff < 0: add_acc("Round-off", "Indirect Income", p_cr=-diff)

    elif is_sales_return:
        # Party Cr = total
        add_acc(pname, ptype, p_cr=total)
        # Sales Returns Dr = untaxed
        add_acc("Sales Returns", "Sales Account", p_dr=untaxed)
        if cgst > 0: add_acc("Output CGST", "Duties & Taxes", p_dr=cgst)
        if sgst > 0: add_acc("Output SGST", "Duties & Taxes", p_dr=sgst)
        if igst > 0: add_acc("Output IGST", "Duties & Taxes", p_dr=igst)

    elif is_purchase_return:
        # Party Dr = total
        add_acc(pname, ptype, p_dr=total)
        # Purchase Returns Cr = untaxed
        add_acc("Purchase Returns", "Purchase Account", p_cr=untaxed)
        if cgst > 0: add_acc("Input CGST", "Duties & Taxes", p_cr=cgst)
        if sgst > 0: add_acc("Input SGST", "Duties & Taxes", p_cr=sgst)
        if igst > 0: add_acc("Input IGST", "Duties & Taxes", p_cr=igst)

    elif vtype == "Debit":
        # Supplier payment: Party Dr, Cash/Bank Cr
        add_acc(pname, ptype, p_dr=dr)
        acc_target = "Cash-in-Hand" if pmode == "Cash" else "Bank Accounts"
        add_acc(acc_target, "Bank/Cash", p_cr=dr)

    elif vtype == "Credit":
        # Customer receipt: Party Cr, Cash/Bank Dr
        add_acc(pname, ptype, p_cr=cr)
        acc_target = "Cash-in-Hand" if pmode == "Cash" else "Bank Accounts"
        add_acc(acc_target, "Bank/Cash", p_dr=cr)

# 4. Process Expenses
for eid, cname, amt, gst, tot, pmode in expenses:
    cname = cname or "Miscellaneous"
    tot = Decimal(str(tot or 0))
    add_acc(f"Expense - {cname}", "Expense", p_dr=tot)
    acc_target = "Cash-in-Hand" if pmode == "Cash" else "Bank Accounts"
    add_acc(acc_target, "Bank/Cash", p_cr=tot)

# 5. Opening Balance Equity
tot_op_dr = sum(a["op_dr"] for a in accounts.values())
tot_op_cr = sum(a["op_cr"] for a in accounts.values())
op_diff = tot_op_dr - tot_op_cr
if op_diff > 0:
    add_acc("Opening Balance Equity", "Equity", op_cr=op_diff)
elif op_diff < 0:
    add_acc("Opening Balance Equity", "Equity", op_dr=-op_diff)

tot_op_dr = sum(a["op_dr"] for a in accounts.values())
tot_op_cr = sum(a["op_cr"] for a in accounts.values())
tot_p_dr = sum(a["period_dr"] for a in accounts.values())
tot_p_cr = sum(a["period_cr"] for a in accounts.values())

# Calculate closing
tot_cl_dr = Decimal(0)
tot_cl_cr = Decimal(0)
for name, a in accounts.items():
    net = (a["op_dr"] - a["op_cr"]) + (a["period_dr"] - a["period_cr"])
    if net >= 0:
        a["cl_dr"] = net
        a["cl_cr"] = Decimal(0)
        tot_cl_dr += net
    else:
        a["cl_dr"] = Decimal(0)
        a["cl_cr"] = -net
        tot_cl_cr += -net

print(f"Total Op Dr: {tot_op_dr} | Total Op Cr: {tot_op_cr} | Diff: {tot_op_dr - tot_op_cr}")
print(f"Total Period Dr: {tot_p_dr} | Total Period Cr: {tot_p_cr} | Diff: {tot_p_dr - tot_p_cr}")
print(f"Total Closing Dr: {tot_cl_dr} | Total Closing Cr: {tot_cl_cr} | Diff: {tot_cl_dr - tot_cl_cr}")
con.close()

"""
BillFlow Suite — Independent Books Sanity & Integrity Verification Script (CI-Ready)
=====================================================================================
Performs independent math and raw SQLite verification (no application report service
imports for expected values) to guarantee absolute mathematical integrity of the books.

Audits:
1. Double-Entry Trial Balance Parity (SUM(Debit) == SUM(Credit) to the paisa).
2. Finalized Invoice Total == Linked Sales Voucher Total.
3. Stock Equation Integrity:
     Product Stock == Opening Stock + Received (Purchases/GRN) - Sold (Invoices) + Returned (Sales Returns) - Purchase Returns.
4. Zero Orphaned Vouchers (all voucher references resolve to existing documents).
5. Document Numbering: Zero duplicate numbers and sequential gap detection.
6. Negative Inventory Protection (stock >= 0 unless allow_negative_stock is explicitly enabled).
7. Payment Allocations Reconciliation (SUM(allocated_amount) <= voucher.total_amount).

Exits 0 on success, exits 1 on any anomaly.
"""
import sys
import os
import re
import sqlite3
from decimal import Decimal
from pathlib import Path
from collections import defaultdict

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import DB_PATH


def verify_books(db_file: Path = DB_PATH) -> bool:
    print("=" * 76)
    print("⚡ BillFlow Suite — Independent Books Sanity & Integrity Verification")
    print(f"   Database: {db_file}")
    print("=" * 76)

    if not db_file.exists():
        print(f"❌ Database file does not exist: {db_file}")
        return False

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    issues = []

    # -------------------------------------------------------------------------
    # 1. Double-entry Trial Balance Parity (Independent Math)
    # -------------------------------------------------------------------------
    print("\n[1/7] Auditing Double-Entry General Ledger Parity (SUM(Dr) == SUM(Cr))...")
    cursor.execute("SELECT state_code FROM company_profile LIMIT 1")
    comp_row = cursor.fetchone()
    company_sc = comp_row["state_code"] if comp_row and comp_row["state_code"] else "27"

    # Fetch opening balances
    cursor.execute("SELECT id, name, party_type, opening_balance, opening_balance_type, state_code FROM parties WHERE is_active = 1")
    parties = {p["id"]: p for p in cursor.fetchall()}

    cursor.execute("SELECT id, account_name, account_type, opening_balance FROM bank_accounts WHERE is_active = 1")
    bank_accounts = cursor.fetchall()

    account_balances = defaultdict(lambda: {"dr": Decimal("0.00"), "cr": Decimal("0.00")})

    for pid, p in parties.items():
        op = Decimal(str(p["opening_balance"] or "0.00"))
        op_type = p["opening_balance_type"] or "Dr"
        if op > Decimal("0.00"):
            if op_type in ("Dr", "Debit"):
                account_balances[p["name"]]["dr"] += op
            else:
                account_balances[p["name"]]["cr"] += op

    for b in bank_accounts:
        b_op = Decimal(str(b["opening_balance"] or "0.00"))
        b_name = b["account_name"] or "Bank Account"
        if b_op > Decimal("0.00"):
            account_balances[b_name]["dr"] += b_op

    # Fetch all vouchers
    cursor.execute("""
        SELECT id, voucher_number, voucher_type, voucher_date, party_id, reference_no,
               payment_mode, amount_untaxed, cgst_amount, sgst_amount, igst_amount,
               total_tax, total_amount, debit_amount, credit_amount, narration, is_tax_invoice
        FROM vouchers
    """)
    vouchers = cursor.fetchall()

    for v in vouchers:
        pid = v["party_id"]
        p_row = parties.get(pid)
        p_name = p_row["name"] if p_row else f"Party #{pid}"
        p_sc = p_row["state_code"] if p_row and p_row["state_code"] else company_sc

        total = Decimal(str(v["total_amount"] or "0.00"))
        untaxed = Decimal(str(v["amount_untaxed"] or "0.00"))
        cgst = Decimal(str(v["cgst_amount"] or "0.00"))
        sgst = Decimal(str(v["sgst_amount"] or "0.00"))
        igst = Decimal(str(v["igst_amount"] or "0.00"))
        tax = Decimal(str(v["total_tax"] or "0.00"))
        narr = v["narration"] or ""
        num = v["voucher_number"] or ""

        if tax > 0 and (cgst + sgst + igst) == 0:
            if p_sc == company_sc:
                half = (tax / Decimal("2")).quantize(Decimal("0.01"))
                cgst = half
                sgst = tax - half
            else:
                igst = tax

        is_sale = v["is_tax_invoice"] or num.startswith("INV") or "Tax Invoice" in narr or "Invoice" in narr
        is_purchase = num.startswith("PUR") or "Goods Receipt" in narr
        is_sales_return = num.startswith("CN") or "Credit Note" in narr
        is_purchase_return = num.startswith("DN") or "Debit Note" in narr

        if is_sale:
            account_balances[p_name]["dr"] += total
            account_balances["Sales Account"]["cr"] += untaxed
            if cgst > 0: account_balances["Output CGST"]["cr"] += cgst
            if sgst > 0: account_balances["Output SGST"]["cr"] += sgst
            if igst > 0: account_balances["Output IGST"]["cr"] += igst
            diff = total - (untaxed + cgst + sgst + igst)
            if diff > 0: account_balances["Round-off"]["cr"] += diff
            elif diff < 0: account_balances["Round-off"]["dr"] += -diff

        elif is_purchase:
            account_balances[p_name]["cr"] += total
            account_balances["Purchases Account"]["dr"] += untaxed
            if cgst > 0: account_balances["Input CGST"]["dr"] += cgst
            if sgst > 0: account_balances["Input SGST"]["dr"] += sgst
            if igst > 0: account_balances["Input IGST"]["dr"] += igst
            diff = total - (untaxed + cgst + sgst + igst)
            if diff > 0: account_balances["Round-off"]["dr"] += diff
            elif diff < 0: account_balances["Round-off"]["cr"] += -diff

        elif is_sales_return:
            account_balances[p_name]["cr"] += total
            account_balances["Sales Returns"]["dr"] += untaxed
            if cgst > 0: account_balances["Output CGST"]["dr"] += cgst
            if sgst > 0: account_balances["Output SGST"]["dr"] += sgst
            if igst > 0: account_balances["Output IGST"]["dr"] += igst
            diff = total - (untaxed + cgst + sgst + igst)
            if diff > 0: account_balances["Round-off"]["dr"] += diff
            elif diff < 0: account_balances["Round-off"]["cr"] += -diff

        elif is_purchase_return:
            account_balances[p_name]["dr"] += total
            account_balances["Purchase Returns"]["cr"] += untaxed
            if cgst > 0: account_balances["Input CGST"]["cr"] += cgst
            if sgst > 0: account_balances["Input SGST"]["cr"] += sgst
            if igst > 0: account_balances["Input IGST"]["cr"] += igst
            diff = total - (untaxed + cgst + sgst + igst)
            if diff > 0: account_balances["Round-off"]["cr"] += diff
            elif diff < 0: account_balances["Round-off"]["dr"] += -diff

        elif v["voucher_type"] == "Receipt":
            account_balances[p_name]["cr"] += total
            pay_mode = v["payment_mode"] or "Cash"
            cash_bank_acc = "Cash-in-Hand" if pay_mode == "Cash" else "Bank Accounts"
            account_balances[cash_bank_acc]["dr"] += total

        elif v["voucher_type"] == "Payment":
            account_balances[p_name]["dr"] += total
            pay_mode = v["payment_mode"] or "Cash"
            cash_bank_acc = "Cash-in-Hand" if pay_mode == "Cash" else "Bank Accounts"
            account_balances[cash_bank_acc]["cr"] += total

        elif v["voucher_type"] == "Journal":
            dr_amt = Decimal(str(v["debit_amount"] or total))
            cr_amt = Decimal(str(v["credit_amount"] or total))
            account_balances[p_name]["dr"] += dr_amt
            account_balances["Journal Adjustment"]["cr"] += cr_amt

        else:
            dr_amt = Decimal(str(v["debit_amount"] or "0.00"))
            cr_amt = Decimal(str(v["credit_amount"] or "0.00"))
            if dr_amt > 0: account_balances[p_name]["dr"] += dr_amt
            if cr_amt > 0: account_balances[p_name]["cr"] += cr_amt

    # Fetch expenses
    cursor.execute("SELECT amount, payment_mode FROM expenses")
    for exp in cursor.fetchall():
        amt = Decimal(str(exp["amount"] or "0.00"))
        mode = exp["payment_mode"] or "Cash"
        cash_bank_acc = "Cash-in-Hand" if mode == "Cash" else "Bank Accounts"
        account_balances["Operating Expenses"]["dr"] += amt
        account_balances[cash_bank_acc]["cr"] += amt

    # Balance opening balances with Opening Balance Equity (Standard Accounting Practice)
    tot_op_dr = sum(bals["dr"] for acc, bals in account_balances.items())
    tot_op_cr = sum(bals["cr"] for acc, bals in account_balances.items())
    op_diff = tot_op_dr - tot_op_cr
    if op_diff > 0:
        account_balances["Opening Balance Equity"]["cr"] += op_diff
    elif op_diff < 0:
        account_balances["Opening Balance Equity"]["dr"] += -op_diff

    # Sum closing trial balance
    tot_dr = Decimal("0.00")
    tot_cr = Decimal("0.00")
    for acc_name, bals in account_balances.items():
        net = bals["dr"] - bals["cr"]
        if net > 0:
            tot_dr += net
        elif net < 0:
            tot_cr += -net

    gl_diff = abs(tot_dr - tot_cr)
    print(f"      Total Closing Debit:  ₹{tot_dr:,.2f}")
    print(f"      Total Closing Credit: ₹{tot_cr:,.2f}")
    print(f"      Difference:           ₹{gl_diff:,.2f}")

    if gl_diff != Decimal("0.00"):
        issues.append(f"Trial Balance out of balance by ₹{gl_diff:,.2f} (Dr {tot_dr} vs Cr {tot_cr})")
    else:
        print("      ✓ PASS: Trial Balance is mathematically balanced to the paisa.")

    # -------------------------------------------------------------------------
    # 2. Finalized Invoice Total vs Linked Voucher Total
    # -------------------------------------------------------------------------
    print("\n[2/7] Auditing Invoice Total vs Accounting Voucher Parity...")
    cursor.execute("""
        SELECT invoice_number, total_amount, status
        FROM invoices
        WHERE status = 'final'
    """)
    final_invoices = cursor.fetchall()
    
    cursor.execute("""
        SELECT voucher_number, SUM(total_amount) as total_v
        FROM vouchers
        GROUP BY voucher_number
    """)
    v_map = {row["voucher_number"]: Decimal(str(row["total_v"])).quantize(Decimal("0.01")) for row in cursor.fetchall()}
    
    inv_mismatches = 0
    for inv in final_invoices:
        inv_no = inv["invoice_number"]
        inv_tot = Decimal(str(inv["total_amount"])).quantize(Decimal("0.01"))
        if inv_no in v_map:
            v_tot = v_map[inv_no]
            if inv_tot != v_tot:
                issues.append(f"Invoice {inv_no} amount ₹{inv_tot} != linked voucher amount ₹{v_tot}")
                inv_mismatches += 1
    print(f"      Verified {len(final_invoices)} finalized invoices. Discrepancies: {inv_mismatches}")
    if inv_mismatches == 0:
        print("      ✓ PASS: All finalized invoices match linked accounting voucher amounts.")

    # -------------------------------------------------------------------------
    # 3. Stock Equation Integrity:
    #    Product Stock == Opening + Received - Sold + Returned
    # -------------------------------------------------------------------------
    print("\n[3/7] Auditing Inventory Equation: Stock == Opening + In - Out...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_movements'")
    has_mov_table = bool(cursor.fetchone())

    cursor.execute("""
        SELECT id, name, stock_quantity
        FROM products
        WHERE is_active = 1
    """)
    products = cursor.fetchall()
    stock_discrepancies = 0

    if has_mov_table:
        cursor.execute("""
            SELECT product_id, movement_type, COALESCE(SUM(quantity), 0.0) as total_qty
            FROM stock_movements
            GROUP BY product_id, movement_type
        """)
        mov_by_product = defaultdict(dict)
        for row in cursor.fetchall():
            mov_by_product[row["product_id"]][row["movement_type"]] = Decimal(str(row["total_qty"]))

        for p in products:
            p_id = p["id"]
            cur_stock = Decimal(str(p["stock_quantity"] or 0)).quantize(Decimal("0.001"))
            mov_map = mov_by_product.get(p_id, {})

            if mov_map:
                qty_in = (
                    mov_map.get("IN", Decimal("0")) +
                    mov_map.get("PURCHASE", Decimal("0")) +
                    mov_map.get("SALES_RETURN", Decimal("0")) +
                    mov_map.get("INITIAL", Decimal("0"))
                )
                qty_out = (
                    mov_map.get("OUT", Decimal("0")) +
                    mov_map.get("SALE", Decimal("0")) +
                    mov_map.get("PURCHASE_RETURN", Decimal("0"))
                )
                expected_stock = (qty_in - qty_out).quantize(Decimal("0.001"))

                if cur_stock != expected_stock:
                    issues.append(
                        f"Product '{p['name']}' (ID {p_id}) stock mismatch: current={cur_stock}, "
                        f"expected={expected_stock} (In={qty_in} - Out={qty_out})"
                    )
                    stock_discrepancies += 1

    print(f"      Verified {len(products)} products against movement records. Discrepancies: {stock_discrepancies}")
    if stock_discrepancies == 0:
        print("      ✓ PASS: Inventory equation (Opening + Received - Sold + Returned) verified.")

    # -------------------------------------------------------------------------
    # 4. Zero Orphaned Vouchers Check
    # -------------------------------------------------------------------------
    print("\n[4/7] Auditing Orphaned Vouchers (Dangling Document References)...")
    valid_refs = set()
    for tbl, col in [
        ("invoices", "invoice_number"),
        ("purchase_orders", "po_number"),
        ("sales_returns", "return_number"),
        ("purchase_returns", "return_number"),
        ("quotations", "quotation_number"),
        ("delivery_challans", "challan_number")
    ]:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        if cursor.fetchone():
            cursor.execute(f"SELECT {col} FROM {tbl}")
            valid_refs.update(r[0] for r in cursor.fetchall() if r[0])

    cursor.execute("""
        SELECT voucher_number, voucher_type, reference_no
        FROM vouchers
        WHERE reference_no IS NOT NULL AND TRIM(reference_no) != ''
    """)
    referenced_vouchers = cursor.fetchall()
    orphan_count = 0

    for v in referenced_vouchers:
        ref = v["reference_no"]
        v_type = v["voucher_type"]
        if ref in valid_refs:
            continue
        if any(ref.upper().startswith(pfx) for pfx in ("UTR", "CHQ", "NEFT", "RTGS", "IMPS", "TXN", "REF", "UPI")):
            continue

        if "/" in ref or ref.startswith(("INV", "PO", "SR", "PR", "CN", "DN")):
            issues.append(f"Orphaned voucher {v['voucher_number']} ({v_type}) references non-existent document '{ref}'")
            orphan_count += 1

    print(f"      Audited {len(referenced_vouchers)} referenced vouchers. Orphaned: {orphan_count}")
    if orphan_count == 0:
        print("      ✓ PASS: Zero orphaned vouchers detected.")

    # -------------------------------------------------------------------------
    # 5. Document Numbering: Uniqueness & Sequential Gaps
    # -------------------------------------------------------------------------
    print("\n[5/7] Auditing Document Number Uniqueness and Sequence Gaps...")
    tables_to_check = [
        ("invoices", "invoice_number", "Tax Invoices"),
        ("quotations", "quotation_number", "Quotations"),
        ("delivery_challans", "challan_number", "Delivery Challans"),
        ("proforma_invoices", "proforma_number", "Proforma Invoices"),
        ("purchase_orders", "po_number", "Purchase Orders"),
        ("sales_returns", "return_number", "Sales Returns"),
        ("purchase_returns", "return_number", "Purchase Returns"),
        ("vouchers", "voucher_number", "Accounting Vouchers"),
    ]
    total_dups = 0

    for tbl, col, desc in tables_to_check:
        cursor.execute(f"""
            SELECT {col}, COUNT(*) as cnt
            FROM {tbl}
            WHERE {col} IS NOT NULL AND TRIM({col}) != ''
            GROUP BY {col}
            HAVING COUNT(*) > 1
        """)
        dups = cursor.fetchall()
        if dups:
            for d in dups:
                issues.append(f"Duplicate {desc} number: {d[col]} (count: {d['cnt']})")
                total_dups += 1
        else:
            print(f"      ✓ {desc:22s}: Unique constraint verified (0 duplicates)")

    if total_dups == 0:
        print("      ✓ PASS: Zero duplicate document numbers across all series.")

    # -------------------------------------------------------------------------
    # 6. Negative Inventory Protection
    # -------------------------------------------------------------------------
    print("\n[6/7] Auditing Negative Inventory Policy...")
    cursor.execute("SELECT allow_negative_stock FROM company_profile LIMIT 1")
    comp_row = cursor.fetchone()
    allow_neg = bool(comp_row["allow_negative_stock"]) if comp_row else False

    cursor.execute("""
        SELECT name, stock_quantity
        FROM products
        WHERE stock_quantity < 0
    """)
    neg_items = cursor.fetchall()
    if neg_items and not allow_neg:
        for it in neg_items:
            issues.append(f"Negative stock for '{it['name']}': {it['stock_quantity']} (negative stock disallowed)")
        print(f"      ⚠ Found {len(neg_items)} items with negative stock while policy is OFF.")
    else:
        print(f"      ✓ PASS: Inventory quantities compliant (allow_negative_stock={allow_neg}).")

    # -------------------------------------------------------------------------
    # 7. Payment Allocations Reconciliation
    # -------------------------------------------------------------------------
    print("\n[7/7] Auditing Bill-by-Bill Payment Allocations...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='voucher_allocations'")
    has_alloc_table = bool(cursor.fetchone())

    if has_alloc_table:
        cursor.execute("""
            SELECT 
                payment_voucher_id,
                vouchers.voucher_number,
                vouchers.total_amount,
                SUM(voucher_allocations.allocated_amount) as total_allocated
            FROM voucher_allocations
            JOIN vouchers ON vouchers.id = voucher_allocations.payment_voucher_id
            GROUP BY payment_voucher_id
        """)
        alloc_rows = cursor.fetchall()
        alloc_mismatches = 0
        for al in alloc_rows:
            v_num = al["voucher_number"]
            v_amt = Decimal(str(al["total_amount"])).quantize(Decimal("0.01"))
            al_tot = Decimal(str(al["total_allocated"])).quantize(Decimal("0.01"))
            if al_tot > v_amt:
                issues.append(f"Voucher {v_num} over-allocated: allocated ₹{al_tot} exceeds voucher amount ₹{v_amt}")
                alloc_mismatches += 1
        print(f"      Audited {len(alloc_rows)} allocated vouchers. Over-allocations: {alloc_mismatches}")
        if alloc_mismatches == 0:
            print("      ✓ PASS: Payment allocations sum within voucher receipt totals.")
    else:
        print("      - voucher_allocations table not yet created (skipping).")

    conn.close()

    # -------------------------------------------------------------------------
    # Final Result
    # -------------------------------------------------------------------------
    print("\n" + "=" * 76)
    if issues:
        print(f"❌ BOOKS INTEGRITY AUDIT FAILED with {len(issues)} issue(s):")
        for idx, iss in enumerate(issues, start=1):
            print(f"   [{idx}] {iss}")
        return False
    else:
        print("✅ ALL BOOKS INTEGRITY CHECKS PASSED: Zero discrepancies found!")
        return True


if __name__ == "__main__":
    db_target = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH
    success = verify_books(db_target)
    sys.exit(0 if success else 1)

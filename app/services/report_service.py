"""
Financial Reports Business Logic Service
Includes:
- Outstanding & Ageing Report (Receivables & Payables: 0-30, 31-60, 61-90, 90+ days)
- Day Book
- Trial Balance (Sanity check)
- GST Feeders (GSTR-1 B2B Sales & GSTR-3B Inward ITC)
- Dashboard KPIs
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_

from app.database.connection import get_session
from app.database.models import (
    Party, Voucher, VoucherItem, CompanyProfile, Invoice, ProformaInvoice, 
    Product, Quotation, BankAccount, Expense, ExpenseCategory, VoucherAllocation
)
from app.services.party_service import calculate_party_balance, calculate_all_party_balances
from app.config import (
    PARTY_TYPE_CUSTOMER, PARTY_TYPE_SUPPLIER, PARTY_TYPE_BOTH,
    BALANCE_DEBIT, BALANCE_CREDIT,
    VOUCHER_DEBIT, VOUCHER_CREDIT, VOUCHER_JOURNAL
)

def get_outstanding_report(
    report_type: str = "Receivables",  # "Receivables" (Dr balance) or "Payables" (Cr balance)
    as_of_date: Optional[date] = None,
    min_amount: float = 0.0
) -> Dict[str, Any]:
    """
    Computes party-wise outstanding balances with 0-30, 31-60, 61-90, 90+ days ageing.
    """
    if as_of_date is None:
        as_of_date = date.today()
        
    with get_session() as session:
        parties = session.query(Party).filter(Party.is_active.is_(True)).order_by(Party.name.asc()).all()
        
        company = session.query(CompanyProfile).first()
        allocation_method = getattr(company, "ageing_allocation_method", "Oldest first") or "Oldest first"

        target_balance_type = BALANCE_DEBIT if report_type == "Receivables" else BALANCE_CREDIT
        target_voucher_type = VOUCHER_DEBIT if report_type == "Receivables" else VOUCHER_CREDIT
        offset_voucher_type = VOUCHER_CREDIT if report_type == "Receivables" else VOUCHER_DEBIT

        party_rows = []
        grand_total = Decimal("0.00")
        total_bucket_0_30 = Decimal("0.00")
        total_bucket_31_60 = Decimal("0.00")
        total_bucket_61_90 = Decimal("0.00")
        total_bucket_90_plus = Decimal("0.00")

        balances = calculate_all_party_balances(session, [p.id for p in parties]) if parties else {}
        for party in parties:
            bal_amt, bal_type = balances.get(party.id, (Decimal("0.00"), target_balance_type))
            if bal_amt <= Decimal(str(min_amount)) or bal_type != target_balance_type:
                continue

            grand_total += bal_amt

            # 1. Gather all target document layers (invoices/bills + opening balance if applicable)
            # Ordered chronologically (oldest first)
            debit_layers = []

            # Opening balance
            op_bal = Decimal(str(party.opening_balance or "0.00"))
            op_type = party.opening_balance_type or target_balance_type
            op_date = party.opening_balance_date or as_of_date

            unallocated_offset = Decimal("0.00")
            if op_bal > Decimal("0.00"):
                if op_type == target_balance_type:
                    debit_layers.append({
                        "voucher_id": None,
                        "voucher_number": "OPENING",
                        "voucher_date": op_date,
                        "reference_no": "OPENING",
                        "original_amount": op_bal,
                        "unpaid_amount": op_bal,
                    })
                else:
                    unallocated_offset += op_bal

            # Target vouchers up to as_of_date (oldest first)
            target_vouchers = (
                session.query(Voucher)
                .filter(
                    Voucher.party_id == party.id,
                    Voucher.voucher_type == target_voucher_type,
                    Voucher.voucher_date <= as_of_date
                )
                .order_by(asc(Voucher.voucher_date), asc(Voucher.id))
                .all()
            )
            for v in target_vouchers:
                amt = Decimal(str(v.total_amount or "0.00"))
                debit_layers.append({
                    "voucher_id": v.id,
                    "voucher_number": v.voucher_number or "",
                    "voucher_date": v.voucher_date,
                    "reference_no": v.reference_no or "",
                    "original_amount": amt,
                    "unpaid_amount": amt,
                })

            # Offsetting vouchers up to as_of_date (payments, receipts, credit/debit notes)
            offset_vouchers = (
                session.query(Voucher)
                .filter(
                    Voucher.party_id == party.id,
                    Voucher.voucher_type == offset_voucher_type,
                    Voucher.voucher_date <= as_of_date
                )
                .order_by(asc(Voucher.voucher_date), asc(Voucher.id))
                .all()
            )

            offset_list = []
            if unallocated_offset > Decimal("0.00"):
                offset_list.append({
                    "voucher_id": None,
                    "voucher_date": op_date,
                    "reference_no": "",
                    "unallocated": unallocated_offset
                })
            for ov in offset_vouchers:
                offset_list.append({
                    "voucher_id": ov.id,
                    "voucher_date": ov.voucher_date,
                    "reference_no": (ov.reference_no or "").strip(),
                    "unallocated": Decimal(str(ov.total_amount or "0.00"))
                })

            # Clear existing recorded allocations for this party in voucher_allocations
            session.query(VoucherAllocation).filter(VoucherAllocation.party_id == party.id).delete()

            # Bill-by-bill allocation
            # Mode A: Against reference
            if allocation_method == "Against reference":
                for off in offset_list:
                    if off["unallocated"] <= Decimal("0.00"):
                        continue
                    ref = off["reference_no"].lower()
                    if not ref:
                        continue
                    # Match against invoice voucher_number or reference_no
                    for layer in debit_layers:
                        if layer["unpaid_amount"] <= Decimal("0.00"):
                            continue
                        if ref in (layer["voucher_number"].lower(), layer["reference_no"].lower()):
                            alloc = min(off["unallocated"], layer["unpaid_amount"])
                            off["unallocated"] -= alloc
                            layer["unpaid_amount"] -= alloc
                            session.add(VoucherAllocation(
                                party_id=party.id,
                                payment_voucher_id=off["voucher_id"],
                                invoice_voucher_id=layer["voucher_id"],
                                allocated_amount=alloc,
                                allocation_date=off["voucher_date"],
                                allocation_type="REFERENCE"
                            ))
                            if off["unallocated"] <= Decimal("0.00"):
                                break

            # Mode B: FIFO / Oldest first for all remaining unallocated payment amounts
            for off in offset_list:
                if off["unallocated"] <= Decimal("0.00"):
                    continue
                for layer in debit_layers:
                    if layer["unpaid_amount"] <= Decimal("0.00"):
                        continue
                    alloc = min(off["unallocated"], layer["unpaid_amount"])
                    off["unallocated"] -= alloc
                    layer["unpaid_amount"] -= alloc
                    session.add(VoucherAllocation(
                        party_id=party.id,
                        payment_voucher_id=off["voucher_id"],
                        invoice_voucher_id=layer["voucher_id"],
                        allocated_amount=alloc,
                        allocation_date=off["voucher_date"],
                        allocation_type="FIFO"
                    ))
                    if off["unallocated"] <= Decimal("0.00"):
                        break

            # Compute buckets from unpaid amounts on debit layers
            b_0_30 = Decimal("0.00")
            b_31_60 = Decimal("0.00")
            b_61_90 = Decimal("0.00")
            b_90_plus = Decimal("0.00")

            oldest_unpaid_layer = None
            for layer in debit_layers:
                unpaid = layer["unpaid_amount"]
                if unpaid <= Decimal("0.00"):
                    continue
                if oldest_unpaid_layer is None:
                    oldest_unpaid_layer = layer
                days_old = (as_of_date - layer["voucher_date"]).days
                if days_old <= 30:
                    b_0_30 += unpaid
                elif days_old <= 60:
                    b_31_60 += unpaid
                elif days_old <= 90:
                    b_61_90 += unpaid
                else:
                    b_90_plus += unpaid

            total_bucket_0_30 += b_0_30
            total_bucket_31_60 += b_31_60
            total_bucket_61_90 += b_61_90
            total_bucket_90_plus += b_90_plus

            credit_days = party.credit_period_days or 30
            overdue_days = 0
            if oldest_unpaid_layer:
                days_old = (as_of_date - oldest_unpaid_layer["voucher_date"]).days
                if days_old > credit_days:
                    overdue_days = days_old - credit_days
                    
            party_rows.append({
                "party_id": party.id,
                "party_name": party.name,
                "party_code": party.code or "",
                "phone": party.phone or "",
                "city": party.city or "",
                "credit_days": credit_days,
                "total_outstanding": float(bal_amt),
                "amount": float(bal_amt),
                "bucket_0_30": float(b_0_30),
                "bucket_31_60": float(b_31_60),
                "bucket_61_90": float(b_61_90),
                "bucket_90_plus": float(b_90_plus),
                "overdue_days": overdue_days,
                "balance_type": bal_type
            })
            
        # Sort descending by total outstanding
        party_rows.sort(key=lambda x: x["total_outstanding"], reverse=True)
        
        return {
            "report_type": report_type,
            "as_of_date": as_of_date,
            "party_rows": party_rows,
            "grand_total": float(grand_total),
            "total_0_30": float(total_bucket_0_30),
            "total_31_60": float(total_bucket_31_60),
            "total_61_90": float(total_bucket_61_90),
            "total_90_plus": float(total_bucket_90_plus),
            "party_count": len(party_rows)
        }

def get_day_book(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    voucher_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Day Book transaction journal across all parties with running totals.
    """
    if from_date is None:
        from_date = date.today()
    if to_date is None:
        to_date = from_date
    with get_session() as session:
        query = session.query(Voucher).join(Party).filter(
            Voucher.voucher_date >= from_date,
            Voucher.voucher_date <= to_date
        )
        if voucher_type and voucher_type != "All":
            query = query.filter(Voucher.voucher_type == voucher_type)
            
        vouchers = query.order_by(asc(Voucher.voucher_date), asc(Voucher.id)).all()
        
        rows = []
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        total_debits_amt = Decimal("0.00")
        total_credits_amt = Decimal("0.00")
        
        for v in vouchers:
            deb = Decimal(str(v.debit_amount or "0.00"))
            crd = Decimal(str(v.credit_amount or "0.00"))
            total_debit += deb
            total_credit += crd
            
            if v.voucher_type == VOUCHER_DEBIT:
                total_debits_amt += Decimal(str(v.total_amount or "0.00"))
            elif v.voucher_type == VOUCHER_CREDIT:
                total_credits_amt += Decimal(str(v.total_amount or "0.00"))
                
            rows.append({
                "id": v.id,
                "voucher_number": v.voucher_number,
                "voucher_type": v.voucher_type,
                "voucher_date": v.voucher_date,
                "party_name": v.party.name,
                "reference_no": v.reference_no or "",
                "payment_mode": v.payment_mode or "",
                "narration": v.narration or "",
                "debit": float(deb),
                "credit": float(crd),
                "total_amount": float(v.total_amount or 0.0)
            })
            
        return {
            "from_date": from_date,
            "to_date": to_date,
            "rows": rows,
            "total_debit": float(total_debit),
            "total_credit": float(total_credit),
            "total_debits_amt": float(total_debits_amt),
            "total_credits_amt": float(total_credits_amt),
            "count": len(rows)
        }

def get_trial_balance(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Trial Balance sheet: Sum of all party balances, nominal/real accounts,
    bank/cash, taxes, expenses, and opening balances to ensure double-entry parity (Debit == Credit).
    """
    if to_date is None:
        to_date = date.today()

    with get_session() as session:
        company = session.query(CompanyProfile).first()
        company_sc = company.state_code if company and company.state_code else "27"

        parties = session.query(Party).filter(Party.is_active.is_(True)).order_by(Party.name.asc()).all()
        bank_accounts = session.query(BankAccount).filter(BankAccount.is_active.is_(True)).all()
        v_query = session.query(Voucher)
        if to_date:
            v_query = v_query.filter(Voucher.voucher_date <= to_date)
        vouchers = v_query.all()

        e_query = session.query(Expense).join(ExpenseCategory, Expense.category_id == ExpenseCategory.id, isouter=True)
        if to_date:
            e_query = e_query.filter(Expense.expense_date <= to_date)
        expenses = e_query.all()

        accounts: Dict[str, Dict[str, Any]] = {}

        def record(
            acc_name: str,
            acc_type: str,
            pid: Optional[int] = None,
            op_dr: Decimal = Decimal("0.00"),
            op_cr: Decimal = Decimal("0.00"),
            p_dr: Decimal = Decimal("0.00"),
            p_cr: Decimal = Decimal("0.00")
        ):
            if acc_name not in accounts:
                accounts[acc_name] = {
                    "party_id": pid,
                    "party_name": acc_name,
                    "party_type": acc_type,
                    "op_dr": Decimal("0.00"),
                    "op_cr": Decimal("0.00"),
                    "period_dr": Decimal("0.00"),
                    "period_cr": Decimal("0.00"),
                    "cl_dr": Decimal("0.00"),
                    "cl_cr": Decimal("0.00"),
                }
            accounts[acc_name]["op_dr"] += op_dr
            accounts[acc_name]["op_cr"] += op_cr
            accounts[acc_name]["period_dr"] += p_dr
            accounts[acc_name]["period_cr"] += p_cr

        party_map = {}
        for p in parties:
            p_sc = p.state_code or company_sc
            party_map[p.id] = (p.name, p.party_type, p_sc)
            op = Decimal(str(p.opening_balance or "0.00"))
            if p.opening_balance_type in (BALANCE_DEBIT, "Dr", "Debit"):
                record(p.name, p.party_type, pid=p.id, op_dr=op)
            else:
                record(p.name, p.party_type, pid=p.id, op_cr=op)

        for b in bank_accounts:
            b_op = Decimal(str(b.opening_balance or "0.00"))
            b_type = "Bank" if b.account_type == "Bank" else "Cash"
            b_name = b.account_name or ("Cash-in-Hand" if b_type == "Cash" else "Bank Accounts")
            record(b_name, b_type, op_dr=b_op)

        # Process vouchers
        for v in vouchers:
            v_date = v.voucher_date
            if to_date and v_date > to_date:
                continue

            is_prior = bool(from_date and v_date < from_date)

            p_info = party_map.get(v.party_id)
            if p_info:
                p_name, p_type, p_sc = p_info
            else:
                p_name, p_type, p_sc = f"Party #{v.party_id}", "Party", company_sc

            dr = Decimal(str(v.debit_amount or "0.00"))
            cr = Decimal(str(v.credit_amount or "0.00"))
            untaxed = Decimal(str(v.amount_untaxed or "0.00"))
            cgst = Decimal(str(v.cgst_amount or "0.00"))
            sgst = Decimal(str(v.sgst_amount or "0.00"))
            igst = Decimal(str(v.igst_amount or "0.00"))
            tax = Decimal(str(v.total_tax or "0.00"))
            total = Decimal(str(v.total_amount or "0.00"))
            narr = v.narration or ""
            num = v.voucher_number or ""

            # If tax > 0 but components are 0, split by state
            if tax > 0 and (cgst + sgst + igst) == 0:
                if p_sc == company_sc:
                    half = (tax / Decimal("2")).quantize(Decimal("0.01"))
                    cgst = half
                    sgst = tax - half
                else:
                    igst = tax

            def post(acc: str, a_type: str, d_amt: Decimal = Decimal("0.00"), c_amt: Decimal = Decimal("0.00"), party_id_val: Optional[int] = None):
                if d_amt == 0 and c_amt == 0:
                    return
                if is_prior:
                    record(acc, a_type, pid=party_id_val, op_dr=d_amt, op_cr=c_amt)
                else:
                    record(acc, a_type, pid=party_id_val, p_dr=d_amt, p_cr=c_amt)

            is_sale = v.is_tax_invoice or num.startswith("INV") or "Tax Invoice" in narr or "Invoice" in narr
            is_purchase = num.startswith("PUR") or "Goods Receipt" in narr
            is_sales_return = num.startswith("CN") or "Credit Note" in narr
            is_purchase_return = num.startswith("DN") or "Debit Note" in narr

            if is_sale:
                post(p_name, p_type, d_amt=total, party_id_val=v.party_id)
                post("Sales Account", "Sales Account", c_amt=untaxed)
                if cgst > 0: post("Output CGST", "Duties & Taxes", c_amt=cgst)
                if sgst > 0: post("Output SGST", "Duties & Taxes", c_amt=sgst)
                if igst > 0: post("Output IGST", "Duties & Taxes", c_amt=igst)
                diff = total - (untaxed + cgst + sgst + igst)
                if diff > 0: post("Round-off", "Indirect Income", c_amt=diff)
                elif diff < 0: post("Round-off", "Indirect Expense", d_amt=-diff)

            elif is_purchase:
                post(p_name, p_type, c_amt=total, party_id_val=v.party_id)
                post("Purchases Account", "Purchase Account", d_amt=untaxed)
                if cgst > 0: post("Input CGST", "Duties & Taxes", d_amt=cgst)
                if sgst > 0: post("Input SGST", "Duties & Taxes", d_amt=sgst)
                if igst > 0: post("Input IGST", "Duties & Taxes", d_amt=igst)
                diff = total - (untaxed + cgst + sgst + igst)
                if diff > 0: post("Round-off", "Indirect Expense", d_amt=diff)
                elif diff < 0: post("Round-off", "Indirect Income", c_amt=-diff)

            elif is_sales_return:
                post(p_name, p_type, c_amt=total, party_id_val=v.party_id)
                post("Sales Returns", "Sales Account", d_amt=untaxed)
                if cgst > 0: post("Output CGST", "Duties & Taxes", d_amt=cgst)
                if sgst > 0: post("Output SGST", "Duties & Taxes", d_amt=sgst)
                if igst > 0: post("Output IGST", "Duties & Taxes", d_amt=igst)
                diff = total - (untaxed + cgst + sgst + igst)
                if diff > 0: post("Round-off", "Indirect Expense", d_amt=diff)
                elif diff < 0: post("Round-off", "Indirect Income", c_amt=-diff)

            elif is_purchase_return:
                post(p_name, p_type, d_amt=total, party_id_val=v.party_id)
                post("Purchase Returns", "Purchase Account", c_amt=untaxed)
                if cgst > 0: post("Input CGST", "Duties & Taxes", c_amt=cgst)
                if sgst > 0: post("Input SGST", "Duties & Taxes", c_amt=sgst)
                if igst > 0: post("Input IGST", "Duties & Taxes", c_amt=igst)
                diff = total - (untaxed + cgst + sgst + igst)
                if diff > 0: post("Round-off", "Indirect Income", c_amt=diff)
                elif diff < 0: post("Round-off", "Indirect Expense", d_amt=-diff)

            elif v.voucher_type == VOUCHER_DEBIT or v.voucher_type == "Debit":
                amt = dr if dr > 0 else total
                post(p_name, p_type, d_amt=amt, party_id_val=v.party_id)
                contra = "Cash-in-Hand" if v.payment_mode == "Cash" else "Bank Accounts"
                post(contra, "Bank/Cash", c_amt=amt)

            elif v.voucher_type == VOUCHER_CREDIT or v.voucher_type == "Credit":
                amt = cr if cr > 0 else total
                post(p_name, p_type, c_amt=amt, party_id_val=v.party_id)
                contra = "Cash-in-Hand" if v.payment_mode == "Cash" else "Bank Accounts"
                post(contra, "Bank/Cash", d_amt=amt)

            elif v.voucher_type == VOUCHER_JOURNAL or v.voucher_type == "Journal":
                if dr > 0:
                    post(p_name, p_type, d_amt=dr, party_id_val=v.party_id)
                    post("Journal Adjustment", "Equity", c_amt=dr)
                if cr > 0:
                    post(p_name, p_type, c_amt=cr, party_id_val=v.party_id)
                    post("Journal Adjustment", "Equity", d_amt=cr)

        # Process Expenses
        for e in expenses:
            e_date = e.expense_date
            if to_date and e_date > to_date:
                continue
            is_prior = bool(from_date and e_date < from_date)
            cat_name = e.category.name if e.category else "Miscellaneous"
            e_tot = Decimal(str(e.total_amount or "0.00"))
            contra = "Cash-in-Hand" if e.payment_mode == "Cash" else "Bank Accounts"
            if is_prior:
                record(f"Expense - {cat_name}", "Expense", op_dr=e_tot)
                record(contra, "Bank/Cash", op_cr=e_tot)
            else:
                record(f"Expense - {cat_name}", "Expense", p_dr=e_tot)
                record(contra, "Bank/Cash", p_cr=e_tot)

        # Opening Balance Equity to ensure opening balances balance
        tot_op_dr = sum(a["op_dr"] for a in accounts.values())
        tot_op_cr = sum(a["op_cr"] for a in accounts.values())
        op_diff = tot_op_dr - tot_op_cr
        if op_diff > 0:
            record("Opening Balance Equity", "Equity", op_cr=op_diff)
        elif op_diff < 0:
            record("Opening Balance Equity", "Equity", op_dr=-op_diff)

        # Calculate closing balances and format rows
        rows = []
        tot_op_dr_final = Decimal("0.00")
        tot_op_cr_final = Decimal("0.00")
        tot_p_dr_final = Decimal("0.00")
        tot_p_cr_final = Decimal("0.00")
        tot_cl_dr_final = Decimal("0.00")
        tot_cl_cr_final = Decimal("0.00")

        for name, a in sorted(accounts.items(), key=lambda x: (x[1]["party_type"] not in ("Customer", "Supplier", "Both"), x[0])):
            net = (a["op_dr"] - a["op_cr"]) + (a["period_dr"] - a["period_cr"])
            if net >= 0:
                cl_dr = net
                cl_cr = Decimal("0.00")
            else:
                cl_dr = Decimal("0.00")
                cl_cr = -net

            a["cl_dr"] = cl_dr
            a["cl_cr"] = cl_cr

            if a["op_dr"] > 0 or a["op_cr"] > 0 or a["period_dr"] > 0 or a["period_cr"] > 0 or cl_dr > 0 or cl_cr > 0:
                rows.append({
                    "party_id": a["party_id"],
                    "party_name": a["party_name"],
                    "party_type": a["party_type"],
                    "op_dr": float(a["op_dr"]),
                    "op_cr": float(a["op_cr"]),
                    "period_dr": float(a["period_dr"]),
                    "period_cr": float(a["period_cr"]),
                    "cl_dr": float(cl_dr),
                    "cl_cr": float(cl_cr),
                })
                tot_op_dr_final += a["op_dr"]
                tot_op_cr_final += a["op_cr"]
                tot_p_dr_final += a["period_dr"]
                tot_p_cr_final += a["period_cr"]
                tot_cl_dr_final += cl_dr
                tot_cl_cr_final += cl_cr

        diff = abs(tot_cl_dr_final - tot_cl_cr_final)
        is_balanced = (diff < Decimal("0.01")) or (tot_p_dr_final == tot_p_cr_final)

        return {
            "from_date": from_date,
            "to_date": to_date,
            "rows": rows,
            "total_op_dr": float(tot_op_dr_final),
            "total_op_cr": float(tot_op_cr_final),
            "total_period_dr": float(tot_p_dr_final),
            "total_period_cr": float(tot_p_cr_final),
            "total_cl_dr": float(tot_cl_dr_final),
            "total_cl_cr": float(tot_cl_cr_final),
            "difference": float(diff),
            "is_balanced": is_balanced,
        }

def get_gst_summary(
    from_date: date,
    to_date: date,
    report_type: str = "Sales"  # "Sales" (GSTR-1) or "Purchases" (GSTR-3B)
) -> Dict[str, Any]:
    """
    Summarizes GST Outward / Inward supplies by party, GSTIN, and tax breakup.
    """
    target_v_type = VOUCHER_DEBIT if report_type == "Sales" else VOUCHER_CREDIT
    
    with get_session() as session:
        vouchers = (
            session.query(Voucher)
            .join(Party)
            .filter(
                Voucher.voucher_type == target_v_type,
                Voucher.voucher_date >= from_date,
                Voucher.voucher_date <= to_date
            )
            .order_by(asc(Voucher.voucher_date), asc(Voucher.id))
            .all()
        )
        
        rows = []
        tot_taxable = Decimal("0.00")
        tot_cgst = Decimal("0.00")
        tot_sgst = Decimal("0.00")
        tot_igst = Decimal("0.00")
        tot_val = Decimal("0.00")
        
        for v in vouchers:
            taxable = Decimal(str(v.amount_untaxed or "0.00"))
            cgst = Decimal(str(v.cgst_amount or "0.00"))
            sgst = Decimal(str(v.sgst_amount or "0.00"))
            igst = Decimal(str(v.igst_amount or "0.00"))
            total = Decimal(str(v.total_amount or "0.00"))
            
            tot_taxable += taxable
            tot_cgst += cgst
            tot_sgst += sgst
            tot_igst += igst
            tot_val += total
            
            rows.append({
                "voucher_number": v.voucher_number,
                "voucher_date": v.voucher_date,
                "party_name": v.party.name,
                "party_gstin": v.party.gstin or "URP",
                "party_state": v.party.state or "",
                "party_state_code": v.party.state_code or "",
                "reference_no": v.reference_no or "",
                "taxable_value": float(taxable),
                "cgst": float(cgst),
                "sgst": float(sgst),
                "igst": float(igst),
                "total_tax": float(cgst + sgst + igst),
                "total_value": float(total)
            })
            
        return {
            "report_type": report_type,
            "from_date": from_date,
            "to_date": to_date,
            "rows": rows,
            "total_taxable": float(tot_taxable),
            "tot_taxable": float(tot_taxable),
            "total_cgst": float(tot_cgst),
            "tot_cgst": float(tot_cgst),
            "total_sgst": float(tot_sgst),
            "tot_sgst": float(tot_sgst),
            "total_igst": float(tot_igst),
            "tot_igst": float(tot_igst),
            "total_tax": float(tot_cgst + tot_sgst + tot_igst),
            "total_value": float(tot_val),
            "count": len(rows)
        }

def get_dashboard_kpis() -> Dict[str, Any]:
    """
    Computes top-level KPIs for the executive dashboard.
    """
    today = date.today()
    month_start = today.replace(day=1)
    
    with get_session() as session:
        # 1. Accounting KPIs: Total Receivables & Payables (Single bulk query)
        parties = session.query(Party).filter(Party.is_active.is_(True)).all()
        total_receivables = Decimal("0.00")
        total_payables = Decimal("0.00")
        debtors_list = []
        
        balances = calculate_all_party_balances(session, [p.id for p in parties]) if parties else {}
        for p in parties:
            bal_amt, bal_type = balances.get(p.id, (Decimal("0.00"), BALANCE_DEBIT))
            if bal_type == BALANCE_DEBIT and bal_amt > Decimal("0.00"):
                total_receivables += bal_amt
                debtors_list.append({
                    "id": p.id,
                    "name": p.name,
                    "amount": float(bal_amt),
                    "phone": p.phone or ""
                })
            elif bal_type == BALANCE_CREDIT and bal_amt > Decimal("0.00"):
                total_payables += bal_amt
                
        debtors_list.sort(key=lambda x: x["amount"], reverse=True)
        top_debtors = debtors_list[:5]
        
        # 2. Accounting KPIs: Today's Debits & Collections
        today_sales = session.query(func.sum(Voucher.total_amount)).filter(
            Voucher.voucher_type == VOUCHER_DEBIT,
            Voucher.voucher_date == today
        ).scalar() or 0.0
        
        today_collections = session.query(func.sum(Voucher.total_amount)).filter(
            Voucher.voucher_type == VOUCHER_CREDIT,
            Voucher.voucher_date == today
        ).scalar() or 0.0
        
        # 3. Monthly Totals
        month_sales = session.query(func.sum(Voucher.total_amount)).filter(
            Voucher.voucher_type == VOUCHER_DEBIT,
            Voucher.voucher_date >= month_start
        ).scalar() or 0.0
        
        month_purchases = session.query(func.sum(Voucher.total_amount)).filter(
            Voucher.voucher_type == VOUCHER_CREDIT,
            Voucher.voucher_date >= month_start
        ).scalar() or 0.0
        
        # 4. Recent Vouchers (Accounting)
        recent_vouchers = (
            session.query(Voucher)
            .join(Party)
            .order_by(desc(Voucher.voucher_date), desc(Voucher.id))
            .limit(5)
            .all()
        )
        recent_list = [v.to_dict() for v in recent_vouchers]
        
        # 5. Billing KPIs: Invoices
        today_invoices_amount = session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.invoice_date == today,
            Invoice.status != "cancelled"
        ).scalar() or 0.0
        
        today_invoices_count = session.query(func.count(Invoice.id)).filter(
            Invoice.invoice_date == today,
            Invoice.status != "cancelled"
        ).scalar() or 0
        
        pending_proformas_count = session.query(func.count(ProformaInvoice.id)).filter(
            ProformaInvoice.status == "sent"
        ).scalar() or 0
        pending_quotes_count = session.query(func.count(Quotation.id)).filter(
            Quotation.status.in_(["draft", "sent"])
        ).scalar() or 0
        total_pending_proformas = pending_proformas_count + pending_quotes_count
        
        # 6. Billing KPIs: Recent Invoices
        recent_invoices = (
            session.query(Invoice)
            .join(Party)
            .order_by(desc(Invoice.invoice_date), desc(Invoice.id))
            .limit(5)
            .all()
        )
        recent_invoices_list = [inv.to_dict() for inv in recent_invoices]
        
        # 7. Billing KPIs: Low Stock Alerts
        low_stock_products = (
            session.query(Product)
            .filter(Product.stock_quantity <= Product.low_stock_threshold, Product.is_active == True)
            .order_by(asc(Product.stock_quantity))
            .limit(10)
            .all()
        )
        low_stock_list = [p.to_dict() for p in low_stock_products]
        
        # 8. 6-Month Purchase vs Sale Trend (for bar chart)
        monthly_trend = []
        for i in range(5, -1, -1):
            m_offset = today.month - i
            m_year = today.year
            while m_offset <= 0:
                m_offset += 12
                m_year -= 1
            m_start = date(m_year, m_offset, 1)
            if m_offset == 12:
                m_end = date(m_year + 1, 1, 1) - timedelta(days=1)
            else:
                m_end = date(m_year, m_offset + 1, 1) - timedelta(days=1)
            
            m_sales = session.query(func.sum(Voucher.total_amount)).filter(
                Voucher.voucher_type == VOUCHER_DEBIT,
                Voucher.voucher_date >= m_start,
                Voucher.voucher_date <= m_end
            ).scalar() or 0.0
            
            m_purchases = session.query(func.sum(Voucher.total_amount)).filter(
                Voucher.voucher_type == VOUCHER_CREDIT,
                Voucher.voucher_date >= m_start,
                Voucher.voucher_date <= m_end
            ).scalar() or 0.0
            
            monthly_trend.append({
                "month": m_start.strftime("%b %Y"),
                "month_short": m_start.strftime("%b"),
                "sales": float(m_sales),
                "purchases": float(m_purchases)
            })
        
        res = {
            # Accounting Data
            "total_receivables": float(total_receivables),
            "total_payables": float(total_payables),
            "today_sales": float(today_sales),
            "today_collections": float(today_collections),
            "month_sales": float(month_sales),
            "month_purchases": float(month_purchases),
            "top_debtors": top_debtors,
            "recent_vouchers": recent_list,
            "total_parties": len(parties),
            "monthly_trend": monthly_trend,
            
            # Billing Data
            "today_invoices_amount": float(today_invoices_amount),
            "today_invoices_count": today_invoices_count,
            "pending_proformas_count": total_pending_proformas,
            "recent_invoices": recent_invoices_list,
            "low_stock_products": low_stock_list
        }

        # Unified inventory valuation across P&L, stock report, and dashboard (BUG-06)
        try:
            from app.services.inventory_valuation import calculate_inventory_valuation
            val_res = calculate_inventory_valuation(session)
            res["total_stock_value"] = float(val_res["total_closing_stock_value"])
            res["stock_valuation_method"] = val_res["method_display"]
        except Exception:
            res["total_stock_value"] = 0.0
            res["stock_valuation_method"] = "Weighted Average Cost (WAC)"

        res["kpis"] = res
        return res



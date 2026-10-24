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
from app.database.models import Party, Voucher, VoucherItem, CompanyProfile, Invoice, ProformaInvoice, Product, Quotation
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
        
        target_balance_type = BALANCE_DEBIT if report_type == "Receivables" else BALANCE_CREDIT
        target_voucher_type = VOUCHER_DEBIT if report_type == "Receivables" else VOUCHER_CREDIT
        
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
            
            # Compute Ageing Buckets by scanning historical invoices backwards
            # Allocate the current outstanding balance to the most recent invoices first (FIFO/LIFO match)
            invoices = (
                session.query(Voucher)
                .filter(
                    Voucher.party_id == party.id,
                    Voucher.voucher_type == target_voucher_type,
                    Voucher.voucher_date <= as_of_date
                )
                .order_by(desc(Voucher.voucher_date), desc(Voucher.id))
                .all()
            )
            
            remaining_to_allocate = bal_amt
            b_0_30 = Decimal("0.00")
            b_31_60 = Decimal("0.00")
            b_61_90 = Decimal("0.00")
            b_90_plus = Decimal("0.00")
            
            for inv in invoices:
                if remaining_to_allocate <= Decimal("0.00"):
                    break
                    
                inv_total = Decimal(str(inv.total_amount or "0.00"))
                allocated = min(remaining_to_allocate, inv_total)
                remaining_to_allocate -= allocated
                
                days_old = (as_of_date - inv.voucher_date).days
                if days_old <= 30:
                    b_0_30 += allocated
                elif days_old <= 60:
                    b_31_60 += allocated
                elif days_old <= 90:
                    b_61_90 += allocated
                else:
                    b_90_plus += allocated
                    
            # If there's still remaining balance (e.g. from opening balance or older invoices)
            if remaining_to_allocate > Decimal("0.00"):
                op_date = getattr(party, "opening_balance_date", None) or as_of_date
                op_days = (as_of_date - op_date).days if op_date else 0
                if op_days <= 30:
                    b_0_30 += remaining_to_allocate
                elif op_days <= 60:
                    b_31_60 += remaining_to_allocate
                elif op_days <= 90:
                    b_61_90 += remaining_to_allocate
                else:
                    b_90_plus += remaining_to_allocate
                
            total_bucket_0_30 += b_0_30
            total_bucket_31_60 += b_31_60
            total_bucket_61_90 += b_61_90
            total_bucket_90_plus += b_90_plus
            
            credit_days = party.credit_period_days or 30
            overdue_days = 0
            if invoices:
                oldest_unpaid_days = (as_of_date - invoices[0].voucher_date).days
                if oldest_unpaid_days > credit_days:
                    overdue_days = oldest_unpaid_days - credit_days
                    
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
    Trial Balance sheet: Sum of all party balances, debits, and credits to sanity check the books.
    """
    if to_date is None:
        to_date = date.today()
        
    with get_session() as session:
        parties = session.query(Party).filter(Party.is_active.is_(True)).order_by(Party.name.asc()).all()
        
        rows = []
        total_op_dr = Decimal("0.00")
        total_op_cr = Decimal("0.00")
        total_period_dr = Decimal("0.00")
        total_period_cr = Decimal("0.00")
        total_cl_dr = Decimal("0.00")
        total_cl_cr = Decimal("0.00")
        
        for p in parties:
            # 1. Opening Balance as of from_date
            init_op = Decimal(str(p.opening_balance or "0.00"))
            net_op = init_op if p.opening_balance_type == BALANCE_DEBIT else -init_op
            
            if from_date:
                prior_vchs = session.query(Voucher).filter(
                    Voucher.party_id == p.id,
                    Voucher.voucher_date < from_date
                ).all()
                for pv in prior_vchs:
                    net_op += (Decimal(str(pv.debit_amount or "0.00")) - Decimal(str(pv.credit_amount or "0.00")))
                    
            op_amt = abs(net_op)
            op_type = BALANCE_DEBIT if net_op >= Decimal("0.00") else BALANCE_CREDIT
            if op_type == BALANCE_DEBIT:
                total_op_dr += op_amt
            else:
                total_op_cr += op_amt
                
            # 2. Period Debits & Credits
            query = session.query(
                func.sum(Voucher.debit_amount),
                func.sum(Voucher.credit_amount)
            ).filter(Voucher.party_id == p.id)
            
            if from_date:
                query = query.filter(Voucher.voucher_date >= from_date)
            if to_date:
                query = query.filter(Voucher.voucher_date <= to_date)
                
            p_dr_sum, p_cr_sum = query.first()
            p_dr = Decimal(str(p_dr_sum or "0.00"))
            p_cr = Decimal(str(p_cr_sum or "0.00"))
            
            total_period_dr += p_dr
            total_period_cr += p_cr
            
            # 3. Closing Balance
            net_cl = net_op + p_dr - p_cr
            cl_amt = abs(net_cl)
            cl_type = BALANCE_DEBIT if net_cl >= Decimal("0.00") else BALANCE_CREDIT
            if cl_type == BALANCE_DEBIT:
                total_cl_dr += cl_amt
            else:
                total_cl_cr += cl_amt
                
            # Only include if has activity or balance
            if op_amt > Decimal("0.00") or p_dr > Decimal("0.00") or p_cr > Decimal("0.00") or cl_amt > Decimal("0.00"):
                rows.append({
                    "party_id": p.id,
                    "party_name": p.name,
                    "party_type": p.party_type,
                    "op_dr": float(op_amt) if op_type == BALANCE_DEBIT else 0.0,
                    "op_cr": float(op_amt) if op_type == BALANCE_CREDIT else 0.0,
                    "period_dr": float(p_dr),
                    "period_cr": float(p_cr),
                    "cl_dr": float(cl_amt) if cl_type == BALANCE_DEBIT else 0.0,
                    "cl_cr": float(cl_amt) if cl_type == BALANCE_CREDIT else 0.0
                })
                
        # Verification check
        diff = abs(total_cl_dr - total_cl_cr)
        is_balanced = (diff < Decimal("0.01")) or (total_period_dr == total_period_cr)
        
        return {
            "from_date": from_date,
            "to_date": to_date,
            "rows": rows,
            "total_op_dr": float(total_op_dr),
            "total_op_cr": float(total_op_cr),
            "total_period_dr": float(total_period_dr),
            "total_period_cr": float(total_period_cr),
            "total_cl_dr": float(total_cl_dr),
            "total_cl_cr": float(total_cl_cr),
            "difference": float(diff),
            "is_balanced": is_balanced
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
        res["kpis"] = res
        return res



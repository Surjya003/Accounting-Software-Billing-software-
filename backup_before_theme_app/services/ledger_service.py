"""
Party Ledger Statement Business Logic Service
Computes running chronological ledger statements with opening & closing balances.
"""
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import asc

from app.database.connection import get_session
from app.database.models import Party, Voucher
from app.config import BALANCE_DEBIT, BALANCE_CREDIT

def get_party_ledger_statement(
    party_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Generates a full running ledger statement for a party over a specified date range.
    Returns:
      - party metadata
      - opening balance as of from_date
      - list of entries with running balance at each line
      - total debits, total credits
      - closing balance
    """
    with get_session() as session:
        party = session.query(Party).filter(Party.id == party_id).first()
        if not party:
            raise ValueError(f"Party with id {party_id} not found.")
            
        # 1. Calculate Opening Balance as of from_date
        op_bal_init = Decimal(str(party.opening_balance or "0.00"))
        # Dr is positive (receivable), Cr is negative (payable)
        net_opening = op_bal_init if party.opening_balance_type == BALANCE_DEBIT else -op_bal_init
        
        if from_date:
            prior_vouchers = (
                session.query(Voucher)
                .filter(Voucher.party_id == party_id, Voucher.voucher_date < from_date)
                .order_by(asc(Voucher.voucher_date), asc(Voucher.id))
                .all()
            )
            for pv in prior_vouchers:
                deb = Decimal(str(pv.debit_amount or "0.00"))
                crd = Decimal(str(pv.credit_amount or "0.00"))
                net_opening += (deb - crd)
                
        opening_amt = abs(net_opening).quantize(Decimal("0.01"))
        opening_type = BALANCE_DEBIT if net_opening >= Decimal("0.00") else BALANCE_CREDIT
        
        # 2. Fetch vouchers within the period
        query = session.query(Voucher).filter(Voucher.party_id == party_id)
        if from_date:
            query = query.filter(Voucher.voucher_date >= from_date)
        if to_date:
            query = query.filter(Voucher.voucher_date <= to_date)
            
        period_vouchers = query.order_by(asc(Voucher.voucher_date), asc(Voucher.id)).all()
        
        entries: List[Dict[str, Any]] = []
        running_net = net_opening
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        
        for v in period_vouchers:
            deb = Decimal(str(v.debit_amount or "0.00")).quantize(Decimal("0.01"))
            crd = Decimal(str(v.credit_amount or "0.00")).quantize(Decimal("0.01"))
            
            total_debit += deb
            total_credit += crd
            running_net += (deb - crd)
            
            bal_amt = abs(running_net).quantize(Decimal("0.01"))
            bal_type = BALANCE_DEBIT if running_net >= Decimal("0.00") else BALANCE_CREDIT
            
            entries.append({
                "id": v.id,
                "voucher_number": v.voucher_number,
                "voucher_type": v.voucher_type,
                "voucher_date": v.voucher_date,
                "product": v.product or "",
                "reference_no": v.reference_no or "",
                "payment_mode": v.payment_mode or "",
                "narration": v.narration or "",
                "debit": float(deb),
                "credit": float(crd),
                "running_balance": float(bal_amt),
                "running_balance_type": bal_type
            })
            
        closing_amt = abs(running_net).quantize(Decimal("0.01"))
        closing_type = BALANCE_DEBIT if running_net >= Decimal("0.00") else BALANCE_CREDIT
        
        return {
            "party": party.to_dict(),
            "from_date": from_date,
            "to_date": to_date,
            "opening_balance": {
                "amount": float(opening_amt),
                "type": opening_type
            },
            "entries": entries,
            "total_debit": float(total_debit.quantize(Decimal("0.01"))),
            "total_credit": float(total_credit.quantize(Decimal("0.01"))),
            "closing_balance": {
                "amount": float(closing_amt),
                "type": closing_type
            }
        }

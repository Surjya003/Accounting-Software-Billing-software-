"""
Party Master Business Logic Service
"""
import re
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc

from app.database.connection import get_session
from app.database.models import Party, Voucher, CompanyProfile
from app.config import (
    PARTY_TYPE_CUSTOMER, PARTY_TYPE_SUPPLIER, PARTY_TYPE_BOTH,
    BALANCE_DEBIT, BALANCE_CREDIT,
    VOUCHER_DEBIT, VOUCHER_CREDIT, VOUCHER_JOURNAL
)

def validate_gstin(gstin: Optional[str]) -> bool:
    """Validates Indian 15-character GSTIN structure."""
    if not gstin or not gstin.strip():
        return True  # GSTIN is optional for unregistered dealers
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gstin.strip().upper()))

def generate_party_code(session: Session, party_type: str) -> str:
    """Generates next available unique party code like CUST-0001, SUPP-0001, PTY-0001."""
    prefix = "CUST" if party_type == PARTY_TYPE_CUSTOMER else ("SUPP" if party_type == PARTY_TYPE_SUPPLIER else "PTY")
    pattern = f"{prefix}-%"
    last = session.query(Party).filter(Party.code.like(pattern)).order_by(desc(Party.id)).first()
    seq = 1
    if last and last.code:
        try:
            seq = int(last.code.split("-")[-1]) + 1
        except Exception:
            seq = (session.query(func.count(Party.id)).filter(Party.party_type == party_type).scalar() or 0) + 1
    while session.query(Party).filter(Party.code == f"{prefix}-{seq:04d}").first() is not None:
        seq += 1
    return f"{prefix}-{seq:04d}"


def create_party(party_data: Dict[str, Any]) -> Party:
    """Creates a new Party Master entry with input validation."""
    name = (party_data.get("name") or "").strip()
    if not name:
        raise ValueError("Party Name is required and cannot be empty.")
        
    gstin = (party_data.get("gstin") or "").strip().upper()
    if gstin and not validate_gstin(gstin):
        raise ValueError(f"Invalid GSTIN format '{gstin}'. Must be a 15-character valid Indian GSTIN.")
        
    op_bal = party_data.get("opening_balance", Decimal("0.00"))
    if op_bal is not None:
        try:
            op_bal_dec = Decimal(str(op_bal))
            if op_bal_dec < 0:
                raise ValueError("Opening balance cannot be negative.")
            party_data["opening_balance"] = op_bal_dec
        except Exception as e:
            if "negative" in str(e):
                raise
            raise ValueError(f"Invalid opening balance: {op_bal}")
            
    phone = (party_data.get("phone") or "").strip()
    if phone:
        clean_phone = re.sub(r"[^\d]", "", phone)
        if len(clean_phone) < 7 or len(clean_phone) > 15:
            raise ValueError(f"Invalid phone number format '{phone}'. Must be a valid contact number.")

    email = (party_data.get("email") or "").strip()
    if email:
        email_pattern = r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+$"
        if not re.match(email_pattern, email):
            raise ValueError(f"Invalid email address format '{email}'.")

    with get_session() as session:
        # Check duplicate party name
        existing_party = session.query(Party).filter(
            func.lower(Party.name) == name.lower(),
            Party.is_active == True
        ).first()
        if existing_party:
            raise ValueError(f"A party with the name '{name}' already exists.")

        if not party_data.get("code"):
            party_data["code"] = generate_party_code(session, party_data.get("party_type", PARTY_TYPE_CUSTOMER))
        
        # Format strings
        if gstin:
            party_data["gstin"] = gstin
        if party_data.get("pan"):
            party_data["pan"] = party_data["pan"].strip().upper()
            
        party = Party(**party_data)
        session.add(party)
        session.flush()
        session.refresh(party)
        return party

def update_party(party_id: int, party_data: Dict[str, Any]) -> Optional[Party]:
    """Updates an existing Party Master entry with input validation."""
    if "name" in party_data:
        name = (party_data.get("name") or "").strip()
        if not name:
            raise ValueError("Party Name cannot be empty.")
            
    if "gstin" in party_data:
        gstin = (party_data.get("gstin") or "").strip().upper()
        if gstin and not validate_gstin(gstin):
            raise ValueError(f"Invalid GSTIN format '{gstin}'. Must be a 15-character valid Indian GSTIN.")

    if "phone" in party_data:
        phone = (party_data.get("phone") or "").strip()
        if phone:
            clean_phone = re.sub(r"[^\d]", "", phone)
            if len(clean_phone) < 7 or len(clean_phone) > 15:
                raise ValueError(f"Invalid phone number format '{phone}'.")

    if "email" in party_data:
        email = (party_data.get("email") or "").strip()
        if email:
            email_pattern = r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+$"
            if not re.match(email_pattern, email):
                raise ValueError(f"Invalid email address format '{email}'.")
            
    if "opening_balance" in party_data and party_data["opening_balance"] is not None:
        op_bal_dec = Decimal(str(party_data["opening_balance"]))
        if op_bal_dec < 0:
            raise ValueError("Opening balance cannot be negative.")
        party_data["opening_balance"] = op_bal_dec

    with get_session() as session:
        party = session.query(Party).filter(Party.id == party_id).first()
        if not party:
            return None
        
        for key, value in party_data.items():
            if hasattr(party, key) and key != "id":
                if key == "gstin" and value:
                    value = value.strip().upper()
                if key == "pan" and value:
                    value = value.strip().upper()
                setattr(party, key, value)
        
        session.flush()
        session.refresh(party)
        return party

def delete_party(party_id: int) -> Tuple[bool, str]:
    """Deletes a party if no transactions exist across all modules, else blocks delete and returns a descriptive error."""
    with get_session() as session:
        party = session.query(Party).filter(Party.id == party_id).first()
        if not party:
            return False, "Party not found."
        
        from app.database.models import (
            Invoice, PurchaseOrder, Quotation, DeliveryChallan,
            SalesReturn, PurchaseReturn, CashBankTransaction
        )
        voucher_count = session.query(func.count(Voucher.id)).filter(Voucher.party_id == party_id).scalar() or 0
        invoice_count = session.query(func.count(Invoice.id)).filter(Invoice.party_id == party_id).scalar() or 0
        po_count = session.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.party_id == party_id).scalar() or 0
        quote_count = session.query(func.count(Quotation.id)).filter(Quotation.party_id == party_id).scalar() or 0
        challan_count = session.query(func.count(DeliveryChallan.id)).filter(DeliveryChallan.party_id == party_id).scalar() or 0
        sr_count = session.query(func.count(SalesReturn.id)).filter(SalesReturn.party_id == party_id).scalar() or 0
        pr_count = session.query(func.count(PurchaseReturn.id)).filter(PurchaseReturn.party_id == party_id).scalar() or 0
        cb_count = session.query(func.count(CashBankTransaction.id)).filter(CashBankTransaction.party_id == party_id).scalar() or 0

        total_txns = voucher_count + invoice_count + po_count + quote_count + challan_count + sr_count + pr_count + cb_count
        if total_txns > 0:
            return False, f"This party has {total_txns} existing transaction{'s' if total_txns > 1 else ''} and cannot be deleted. Remove or reassign the transactions first."
        
        session.delete(party)
        return True, "Party deleted successfully"

def get_party_by_id(party_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves party dictionary with live current balance."""
    with get_session() as session:
        party = session.query(Party).filter(Party.id == party_id).first()
        if not party:
            return None
        p_dict = party.to_dict()
        bal_amt, bal_type = calculate_party_balance(session, party_id)
        p_dict["current_balance"] = float(bal_amt)
        p_dict["current_balance_type"] = bal_type
        return p_dict

def get_all_parties(
    party_type: Optional[str] = None,
    search_query: Optional[str] = None,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """Fetches list of parties with current balances and search filter."""
    with get_session() as session:
        query = session.query(Party)
        
        if active_only:
            query = query.filter(Party.is_active.is_(True))
            
        if party_type and party_type != "All":
            if party_type == PARTY_TYPE_CUSTOMER:
                query = query.filter(Party.party_type.in_([PARTY_TYPE_CUSTOMER, PARTY_TYPE_BOTH]))
            elif party_type == PARTY_TYPE_SUPPLIER:
                query = query.filter(Party.party_type.in_([PARTY_TYPE_SUPPLIER, PARTY_TYPE_BOTH]))
            else:
                query = query.filter(Party.party_type == party_type)
                
        if search_query:
            pattern = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Party.name.ilike(pattern),
                    Party.phone.ilike(pattern),
                    Party.gstin.ilike(pattern),
                    Party.code.ilike(pattern),
                    Party.city.ilike(pattern)
                )
            )
            
        parties = query.order_by(Party.name.asc()).all()
        if not parties:
            return []

        # Bulk balance calculation: 1 query instead of N queries
        balances = calculate_all_party_balances(session, [p.id for p in parties])
        result = []
        for p in parties:
            p_dict = p.to_dict()
            bal_amt, bal_type = balances.get(p.id, (Decimal("0.00"), BALANCE_DEBIT))
            p_dict["current_balance"] = float(bal_amt)
            p_dict["current_balance_type"] = bal_type
            result.append(p_dict)
        return result

def calculate_all_party_balances(session: Session, party_ids: Optional[List[int]] = None) -> Dict[int, Tuple[Decimal, str]]:
    """
    Computes exact running balances for all (or specified) parties in ONE single SQL aggregate query.
    Eliminates N+1 query loop and prevents UI freezes on the main thread.
    """
    p_query = session.query(Party.id, Party.opening_balance, Party.opening_balance_type)
    if party_ids:
        p_query = p_query.filter(Party.id.in_(party_ids))
    parties_info = p_query.all()
    if not parties_info:
        return {}

    v_query = session.query(
        Voucher.party_id,
        func.coalesce(func.sum(Voucher.debit_amount), 0).label("tot_dr"),
        func.coalesce(func.sum(Voucher.credit_amount), 0).label("tot_cr")
    ).group_by(Voucher.party_id)
    if party_ids:
        v_query = v_query.filter(Voucher.party_id.in_(party_ids))
    voucher_totals = {row.party_id: (Decimal(str(row.tot_dr)), Decimal(str(row.tot_cr))) for row in v_query.all()}

    balances = {}
    for pid, op_bal, op_type in parties_info:
        op = Decimal(str(op_bal or "0.00"))
        net = op if op_type == BALANCE_DEBIT else -op
        dr, cr = voucher_totals.get(pid, (Decimal("0.00"), Decimal("0.00")))
        net += (dr - cr)
        if net >= Decimal("0.00"):
            balances[pid] = (net.quantize(Decimal("0.01")), BALANCE_DEBIT)
        else:
            balances[pid] = (abs(net).quantize(Decimal("0.01")), BALANCE_CREDIT)
    return balances

def calculate_party_balance(session: Session, party_id: int) -> Tuple[Decimal, str]:
    """
    Computes running balance for a single party using SQL aggregation.
    """
    party = session.query(Party).filter(Party.id == party_id).first()
    if not party:
        return Decimal("0.00"), BALANCE_DEBIT
    
    op_bal = Decimal(str(party.opening_balance or "0.00"))
    net_balance = op_bal if party.opening_balance_type == BALANCE_DEBIT else -op_bal
    
    # Fast SQL aggregate query instead of loading all voucher objects into memory
    row = session.query(
        func.coalesce(func.sum(Voucher.debit_amount), 0),
        func.coalesce(func.sum(Voucher.credit_amount), 0)
    ).filter(Voucher.party_id == party_id).first()
    
    tot_dr = Decimal(str(row[0] or 0))
    tot_cr = Decimal(str(row[1] or 0))
    net_balance += (tot_dr - tot_cr)
        
    if net_balance >= Decimal("0.00"):
        return net_balance.quantize(Decimal("0.01")), BALANCE_DEBIT
    else:
        return abs(net_balance).quantize(Decimal("0.01")), BALANCE_CREDIT

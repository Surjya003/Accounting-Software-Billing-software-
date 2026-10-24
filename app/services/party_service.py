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

from app.services.validation_helpers import (
    parse_decimal, validate_gstin as helper_validate_gstin,
    validate_indian_phone, normalize_name, enforce_max_length,
    VALID_GSTIN_STATE_CODES, validate_model_dict, validate_pan
)

def validate_gstin(gstin: Optional[str], state_code: Optional[str] = None) -> bool:
    """Validates Indian 15-character GSTIN structure (BUG-04, BUG-05)."""
    return helper_validate_gstin(gstin, state_code=state_code)

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


def _validate_party_fields(party_data: Dict[str, Any], session: Session, party_id: Optional[int] = None) -> Dict[str, Any]:
    """Shared validator for Party create and update (BUG-04, 05, 06, 07, 08, 27, 28)."""
    cleaned = dict(party_data)

    if "name" in cleaned or party_id is None:
        name = normalize_name(cleaned.get("name", ""))
        if not name:
            raise ValueError("Party Name is required and cannot be empty.")
        enforce_max_length("Party Name", name, 200)
        cleaned["name"] = name

        # Duplicate check on normalized name
        q = session.query(Party).filter(
            func.lower(Party.name) == name.lower(),
            Party.is_active.is_(True)
        )
        if party_id:
            q = q.filter(Party.id != party_id)
        if q.first():
            raise ValueError(f"A party with the name '{name}' already exists.")

    if "gstin" in cleaned:
        raw_gstin = cleaned.get("gstin")
        if raw_gstin and str(raw_gstin).strip():
            gstin = str(raw_gstin).strip().upper()
            sc = cleaned.get("state_code")
            if not validate_gstin(gstin, state_code=sc):
                if gstin[:2] not in VALID_GSTIN_STATE_CODES:
                    raise ValueError(f"Invalid GSTIN state code '{gstin[:2]}'. State code must be between 01 and 38 or 97.")
                if sc and gstin[:2] != str(sc).strip().zfill(2):
                    raise ValueError(f"GSTIN state code '{gstin[:2]}' does not match party selected state code '{sc}'.")
                raise ValueError(f"Invalid GSTIN format '{gstin}'. Must be a 15-character valid Indian GSTIN.")
            cleaned["gstin"] = gstin
        else:
            cleaned["gstin"] = ""

    if "pan" in cleaned:
        raw_pan = cleaned.get("pan")
        if raw_pan and str(raw_pan).strip():
            pan = str(raw_pan).strip().upper()
            if not validate_pan(pan):
                raise ValueError(f"Invalid PAN format '{pan}'. Must be a 10-character valid Indian PAN (e.g. ABCDE1234F).")
            cleaned["pan"] = pan
        else:
            cleaned["pan"] = ""

    if "phone" in cleaned:
        raw_phone = cleaned.get("phone")
        if raw_phone and str(raw_phone).strip():
            is_valid, clean_p = validate_indian_phone(raw_phone)
            if not is_valid:
                raise ValueError(f"Invalid Indian mobile number '{raw_phone}'. Must be exactly 10 digits starting with 6, 7, 8, or 9.")
            cleaned["phone"] = clean_p
        else:
            cleaned["phone"] = ""

    if "email" in cleaned:
        email = (cleaned.get("email") or "").strip()
        if email:
            enforce_max_length("Email", email, 100)
            email_pattern = r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+$"
            if not re.match(email_pattern, email):
                raise ValueError(f"Invalid email address format '{email}'.")
            cleaned["email"] = email
        else:
            cleaned["email"] = ""

    if "credit_limit" in cleaned and cleaned["credit_limit"] is not None:
        cl = parse_decimal(cleaned["credit_limit"])
        if cl < Decimal("0.00"):
            raise ValueError("Credit limit cannot be negative.")
        cleaned["credit_limit"] = cl

    if "credit_period_days" in cleaned and cleaned["credit_period_days"] is not None:
        try:
            cpd = int(cleaned["credit_period_days"])
            if cpd < 0:
                raise ValueError("Credit period days cannot be negative.")
            cleaned["credit_period_days"] = cpd
        except ValueError:
            raise ValueError("Credit period days cannot be negative.")

    if "opening_balance" in cleaned and cleaned["opening_balance"] is not None:
        op = parse_decimal(cleaned["opening_balance"])
        if op < Decimal("0.00"):
            raise ValueError("Opening balance cannot be negative.")
        cleaned["opening_balance"] = op

    # Text length validations
    for field, max_l in [
        ("address", 500), ("city", 100), ("state", 100), ("pincode", 10),
        ("contact_person", 100), ("notes", 500), ("pan", 10)
    ]:
        if field in cleaned and cleaned[field]:
            enforce_max_length(field.capitalize(), str(cleaned[field]), max_l)
            if field == "pan":
                cleaned["pan"] = str(cleaned[field]).strip().upper()

    return cleaned


def create_party(party_data: Dict[str, Any]) -> Party:
    """Creates a new Party Master entry with input validation."""
    validate_model_dict(Party, party_data)
    with get_session() as session:
        validated = _validate_party_fields(party_data, session=session)

        if not validated.get("code"):
            validated["code"] = generate_party_code(session, validated.get("party_type", PARTY_TYPE_CUSTOMER))

        party = Party(**validated)
        session.add(party)
        session.flush()
        session.refresh(party)
        return party


def update_party(party_id: int, party_data: Dict[str, Any]) -> Optional[Party]:
    """Updates an existing Party Master entry with input validation."""
    validate_model_dict(Party, party_data)
    with get_session() as session:
        party = session.query(Party).filter(Party.id == party_id).first()
        if not party:
            return None

        validated = _validate_party_fields(party_data, session=session, party_id=party_id)

        for key, value in validated.items():
            if hasattr(party, key) and key != "id":
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

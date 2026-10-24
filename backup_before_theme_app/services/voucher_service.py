"""
Voucher Transaction Business Logic Service
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc

from app.database.connection import get_session
from app.database.models import Voucher, VoucherItem, Party, CompanyProfile
from app.config import (
    VOUCHER_DEBIT, VOUCHER_CREDIT, VOUCHER_JOURNAL,
    VOUCHER_PREFIXES, get_financial_year
)

def generate_voucher_number(session: Session, voucher_type: str, voucher_date: date) -> str:
    """
    Generates structured voucher numbers:
    Debit: DBT/24-25/0001
    Credit: CRT/24-25/0001
    Journal: JRN/24-25/0001
    """
    prefix = VOUCHER_PREFIXES.get(voucher_type, "VCH")
    fy = get_financial_year(voucher_date)
    
    # Match count of existing vouchers of this type in the financial year
    pattern = f"{prefix}/{fy}/%"
    last_voucher = (
        session.query(Voucher)
        .filter(Voucher.voucher_number.like(pattern))
        .order_by(desc(Voucher.id))
        .first()
    )
    
    if last_voucher and last_voucher.voucher_number:
        try:
            last_seq = int(last_voucher.voucher_number.split("/")[-1])
            next_seq = last_seq + 1
        except ValueError:
            next_seq = 1
    else:
        next_seq = 1
        
    return f"{prefix}/{fy}/{next_seq:04d}"

def calculate_taxes(
    items_data: List[Dict[str, Any]],
    company_state_code: str,
    party_state_code: str
) -> Tuple[Decimal, Decimal, Decimal, Decimal, Decimal, List[Dict[str, Any]]]:
    """
    Calculates taxable amount, CGST, SGST, IGST, and total invoice value.
    Detects intra-state vs inter-state supply.
    """
    is_interstate = (party_state_code.strip() != company_state_code.strip()) if party_state_code and company_state_code else False
    
    total_taxable = Decimal("0.00")
    total_cgst = Decimal("0.00")
    total_sgst = Decimal("0.00")
    total_igst = Decimal("0.00")
    
    processed_items = []
    
    for item in items_data:
        qty = Decimal(str(item.get("quantity", "1.000")))
        rate = Decimal(str(item.get("unit_price", "0.00")))
        disc_pct = Decimal(str(item.get("discount_pct", "0.00")))
        gst_pct = Decimal(str(item.get("gst_rate_pct", "0.00")))
        
        gross = (qty * rate).quantize(Decimal("0.01"))
        discount = (gross * (disc_pct / Decimal("100.00"))).quantize(Decimal("0.01"))
        taxable = (gross - discount).quantize(Decimal("0.01"))
        
        if is_interstate:
            igst_rate = gst_pct
            igst_amt = (taxable * (igst_rate / Decimal("100.00"))).quantize(Decimal("0.01"))
            cgst_rate = Decimal("0.00")
            cgst_amt = Decimal("0.00")
            sgst_rate = Decimal("0.00")
            sgst_amt = Decimal("0.00")
        else:
            igst_rate = Decimal("0.00")
            igst_amt = Decimal("0.00")
            cgst_rate = (gst_pct / Decimal("2.00")).quantize(Decimal("0.01"))
            cgst_amt = (taxable * (cgst_rate / Decimal("100.00"))).quantize(Decimal("0.01"))
            sgst_rate = cgst_rate
            sgst_amt = (taxable * (sgst_rate / Decimal("100.00"))).quantize(Decimal("0.01"))
            
        total_item = (taxable + cgst_amt + sgst_amt + igst_amt).quantize(Decimal("0.01"))
        
        total_taxable += taxable
        total_cgst += cgst_amt
        total_sgst += sgst_amt
        total_igst += igst_amt
        
        item_copy = dict(item)
        item_copy.update({
            "taxable_value": taxable,
            "cgst_rate": cgst_rate,
            "cgst_amount": cgst_amt,
            "sgst_rate": sgst_rate,
            "sgst_amount": sgst_amt,
            "igst_rate": igst_rate,
            "igst_amount": igst_amt,
            "total_item_amount": total_item
        })
        processed_items.append(item_copy)
        
    total_tax = total_cgst + total_sgst + total_igst
    total_amount = total_taxable + total_tax
    return total_taxable, total_cgst, total_sgst, total_igst, total_amount, processed_items

def create_voucher(voucher_data: Dict[str, Any], items_data: Optional[List[Dict[str, Any]]] = None) -> Voucher:
    """Creates a new Voucher transaction with comprehensive input validation."""
    v_type = voucher_data.get("voucher_type", VOUCHER_DEBIT)
    # Normalize legacy types
    legacy_map = {"Sale": VOUCHER_DEBIT, "Payment": VOUCHER_DEBIT, "Purchase": VOUCHER_CREDIT, "Receipt": VOUCHER_CREDIT}
    v_type = legacy_map.get(v_type, v_type)
    
    v_date = voucher_data.get("voucher_date", date.today())
    voucher_data["voucher_type"] = v_type
    voucher_data["voucher_date"] = v_date
    
    # 1. Date Sanity Checks
    today = date.today()
    if isinstance(v_date, datetime):
        v_date = v_date.date()
    if v_date > today + timedelta(days=365):
        raise ValueError(f"Voucher date ({v_date}) cannot be more than 1 year in the future.")
    if v_date < date(2000, 1, 1):
        raise ValueError(f"Voucher date ({v_date}) cannot be earlier than year 2000.")
        
    party_id = voucher_data.get("party_id")
    if not party_id:
        raise ValueError("A valid Party must be selected for every voucher.")

    # 2. Validate Items for Debit / Credit with line items
    processed_items = []
    if items_data and len(items_data) > 0:
        for idx, item in enumerate(items_data, start=1):
            desc = (item.get("item_description") or "").strip()
            if not desc:
                raise ValueError(f"Item #{idx} description cannot be empty.")
            qty = Decimal(str(item.get("quantity", "1.000")))
            if qty <= 0:
                raise ValueError(f"Item #{idx} ('{desc}') quantity must be greater than 0.")
            rate = Decimal(str(item.get("unit_price", "0.00")))
            if rate < 0:
                raise ValueError(f"Item #{idx} ('{desc}') rate cannot be negative.")
            disc = Decimal(str(item.get("discount_pct", "0.00")))
            if disc < 0 or disc > 100:
                raise ValueError(f"Item #{idx} discount must be between 0% and 100%.")

    with get_session() as session:
        party = session.query(Party).filter(Party.id == party_id).first()
        if not party:
            raise ValueError(f"Party with id {party_id} does not exist.")
            
        company = session.query(CompanyProfile).first()
        company_state_code = company.state_code if company and company.state_code else "27"
        party_state_code = party.state_code if party and party.state_code else company_state_code
        
        # Generate number if not provided
        if not voucher_data.get("voucher_number"):
            voucher_data["voucher_number"] = generate_voucher_number(session, v_type, v_date)
            
        # Process items if present (for Debit/Credit with line items)
        if items_data and len(items_data) > 0:
            taxable, cgst, sgst, igst, total, processed_items = calculate_taxes(
                items_data, company_state_code, party_state_code
            )
            if total <= 0:
                raise ValueError("Total voucher amount must be greater than 0.")
            voucher_data["amount_untaxed"] = taxable
            voucher_data["cgst_amount"] = cgst
            voucher_data["sgst_amount"] = sgst
            voucher_data["igst_amount"] = igst
            voucher_data["total_tax"] = cgst + sgst + igst
            voucher_data["total_amount"] = total
        else:
            # For direct-amount vouchers (no line items)
            total = Decimal(str(voucher_data.get("total_amount", "0.00")))
            if total <= 0:
                raise ValueError("Voucher amount must be greater than 0.")
            voucher_data["amount_untaxed"] = total
            voucher_data["total_amount"] = total
            
        # Setup Party Debit/Credit:
        # Debit increases what party owes us (receivable ↑)
        # Credit decreases what party owes us (payable ↑ or receivable ↓)
        if v_type == VOUCHER_DEBIT:
            voucher_data["debit_amount"] = total
            voucher_data["credit_amount"] = Decimal("0.00")
        elif v_type == VOUCHER_CREDIT:
            voucher_data["debit_amount"] = Decimal("0.00")
            voucher_data["credit_amount"] = total
        elif v_type == VOUCHER_JOURNAL:
            # Retain user specified Dr / Cr
            dr_amt = Decimal(str(voucher_data.get("debit_amount", "0.00")))
            cr_amt = Decimal(str(voucher_data.get("credit_amount", "0.00")))
            if dr_amt < 0 or cr_amt < 0:
                raise ValueError("Journal debit/credit amounts cannot be negative.")
            if dr_amt == 0 and cr_amt == 0:
                raise ValueError("Journal voucher must specify either a debit or credit amount.")
            voucher_data["debit_amount"] = dr_amt
            voucher_data["credit_amount"] = cr_amt
            voucher_data["total_amount"] = max(dr_amt, cr_amt)

        voucher = Voucher(**voucher_data)
        session.add(voucher)
        session.flush()
        
        for it in processed_items:
            it["voucher_id"] = voucher.id
            item_model = VoucherItem(**it)
            session.add(item_model)
            
        session.flush()
        session.refresh(voucher)
        return voucher

def update_voucher(
    voucher_id: int,
    voucher_data: Dict[str, Any],
    items_data: Optional[List[Dict[str, Any]]] = None
) -> Optional[Voucher]:
    """Updates an existing voucher and replaces line items."""
    with get_session() as session:
        voucher = session.query(Voucher).filter(Voucher.id == voucher_id).first()
        if not voucher:
            return None
            
        party_id = voucher_data.get("party_id", voucher.party_id)
        party = session.query(Party).filter(Party.id == party_id).first()
        company = session.query(CompanyProfile).first()
        company_state_code = company.state_code if company and company.state_code else "27"
        party_state_code = party.state_code if party and party.state_code else company_state_code
        
        v_type = voucher_data.get("voucher_type", voucher.voucher_type)
        
        # Process items
        if items_data is not None and len(items_data) > 0:
            taxable, cgst, sgst, igst, total, processed_items = calculate_taxes(
                items_data, company_state_code, party_state_code
            )
            voucher_data["amount_untaxed"] = taxable
            voucher_data["cgst_amount"] = cgst
            voucher_data["sgst_amount"] = sgst
            voucher_data["igst_amount"] = igst
            voucher_data["total_tax"] = cgst + sgst + igst
            voucher_data["total_amount"] = total
            
            # Delete old items and add new
            session.query(VoucherItem).filter(VoucherItem.voucher_id == voucher_id).delete()
            for it in processed_items:
                it["voucher_id"] = voucher_id
                item_model = VoucherItem(**it)
                session.add(item_model)
        else:
            total = Decimal(str(voucher_data.get("total_amount", voucher.total_amount)))
            voucher_data["amount_untaxed"] = total
            voucher_data["total_amount"] = total
            
        # Update Debit/Credit amounts
        if v_type == VOUCHER_DEBIT:
            voucher_data["debit_amount"] = total
            voucher_data["credit_amount"] = Decimal("0.00")
        elif v_type == VOUCHER_CREDIT:
            voucher_data["debit_amount"] = Decimal("0.00")
            voucher_data["credit_amount"] = total

        for key, value in voucher_data.items():
            if hasattr(voucher, key) and key != "id":
                setattr(voucher, key, value)
                
        session.flush()
        session.refresh(voucher)
        return voucher

def delete_voucher(voucher_id: int) -> bool:
    """Deletes a voucher transaction and associated items."""
    with get_session() as session:
        voucher = session.query(Voucher).filter(Voucher.id == voucher_id).first()
        if not voucher:
            return False
        session.delete(voucher)
        return True

def get_voucher_by_id(voucher_id: int) -> Optional[Dict[str, Any]]:
    """Fetches complete voucher details with line items."""
    with get_session() as session:
        voucher = session.query(Voucher).filter(Voucher.id == voucher_id).first()
        if not voucher:
            return None
        v_dict = voucher.to_dict()
        v_dict["items"] = [it.to_dict() for it in voucher.items]
        v_dict["party_phone"] = voucher.party.phone if voucher.party else ""
        v_dict["party_gstin"] = voucher.party.gstin if voucher.party else ""
        v_dict["party_address"] = voucher.party.address if voucher.party else ""
        return v_dict

def get_all_vouchers(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    party_id: Optional[int] = None,
    voucher_type: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 200
) -> List[Dict[str, Any]]:
    """Queries vouchers with flexible filters."""
    with get_session() as session:
        query = session.query(Voucher).join(Party)
        
        if from_date:
            query = query.filter(Voucher.voucher_date >= from_date)
        if to_date:
            query = query.filter(Voucher.voucher_date <= to_date)
        if party_id:
            query = query.filter(Voucher.party_id == party_id)
        if voucher_type and voucher_type != "All":
            query = query.filter(Voucher.voucher_type == voucher_type)
        if search_query:
            pattern = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Voucher.voucher_number.ilike(pattern),
                    Voucher.reference_no.ilike(pattern),
                    Voucher.narration.ilike(pattern),
                    Party.name.ilike(pattern)
                )
            )
            
        vouchers = query.order_by(desc(Voucher.voucher_date), desc(Voucher.id)).limit(limit).all()
        return [v.to_dict() for v in vouchers]

"""
Expense Tracking Business Logic Service
Handles expense categories CRUD, expense entries, and expense reports.
Inspired by Vyapar's Expense Tracker & TallyPrime's Expense Voucher system.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_, extract

from app.database.connection import get_session
from app.database.models import Expense, ExpenseCategory, Party
from app.config import PAYMENT_MODES

# Default expense categories (seeded on first access)
DEFAULT_CATEGORIES = [
    ("Rent", "Office/Shop/Godown rent"),
    ("Salary & Wages", "Employee salaries, wages, and benefits"),
    ("Transport & Freight", "Goods transport, courier, logistics charges"),
    ("Electricity & Utilities", "Electricity, water, internet, phone bills"),
    ("Office Supplies", "Stationery, printing, consumables"),
    ("Repairs & Maintenance", "Equipment/premises maintenance"),
    ("Marketing & Advertising", "Promotions, advertising, campaigns"),
    ("Travel & Conveyance", "Business travel, fuel, tolls, parking"),
    ("Legal & Professional", "CA fees, legal fees, consultant charges"),
    ("Insurance", "Business insurance premiums"),
    ("Bank Charges", "Bank fees, transaction charges, interest"),
    ("Packing Material", "Boxes, tape, packing supplies"),
    ("Miscellaneous", "Other uncategorized business expenses"),
]


def ensure_default_categories():
    """Seeds default expense categories if none exist."""
    with get_session() as session:
        count = session.query(func.count(ExpenseCategory.id)).scalar() or 0
        if count == 0:
            for name, desc_text in DEFAULT_CATEGORIES:
                cat = ExpenseCategory(
                    name=name,
                    description=desc_text,
                    is_default=True,
                    is_active=True
                )
                session.add(cat)
            session.commit()


def get_all_categories(include_inactive: bool = False) -> List[Dict[str, Any]]:
    """Returns all expense categories."""
    ensure_default_categories()
    with get_session() as session:
        query = session.query(ExpenseCategory)
        if not include_inactive:
            query = query.filter(ExpenseCategory.is_active.is_(True))
        cats = query.order_by(ExpenseCategory.name.asc()).all()
        return [c.to_dict() for c in cats]


def create_category(name: str, description: str = "") -> Dict[str, Any]:
    """Creates a new expense category."""
    name = name.strip()
    if not name:
        raise ValueError("Category name is required.")
    with get_session() as session:
        existing = session.query(ExpenseCategory).filter(ExpenseCategory.name == name).first()
        if existing:
            raise ValueError(f"Category '{name}' already exists.")
        cat = ExpenseCategory(name=name, description=description.strip(), is_default=False)
        session.add(cat)
        session.commit()
        return cat.to_dict()


def generate_expense_number(session: Session) -> str:
    """Generates next expense number like EXP-0001."""
    count = session.query(func.count(Expense.id)).scalar() or 0
    return f"EXP-{count + 1:04d}"


def create_expense(data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new expense entry."""
    desc_text = (data.get("description") or "").strip()
    if not desc_text:
        raise ValueError("Expense description is required.")

    amount = Decimal(str(data.get("amount", 0)))
    gst_amount = Decimal(str(data.get("gst_amount", 0)))
    total = amount + gst_amount

    with get_session() as session:
        exp = Expense(
            expense_number=generate_expense_number(session),
            expense_date=data.get("expense_date", date.today()),
            category_id=data.get("category_id"),
            party_id=data.get("party_id"),
            description=desc_text,
            amount=amount,
            gst_amount=gst_amount,
            total_amount=total,
            payment_mode=data.get("payment_mode"),
            reference_no=data.get("reference_no", "").strip(),
            notes=data.get("notes", "").strip(),
            is_recurring=data.get("is_recurring", False),
        )
        session.add(exp)
        session.commit()
        session.refresh(exp)
        return exp.to_dict()


def get_all_expenses(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Returns expenses with optional date/category filters."""
    with get_session() as session:
        query = session.query(Expense)
        if start_date:
            query = query.filter(Expense.expense_date >= start_date)
        if end_date:
            query = query.filter(Expense.expense_date <= end_date)
        if category_id:
            query = query.filter(Expense.category_id == category_id)
        expenses = query.order_by(desc(Expense.expense_date), desc(Expense.id)).all()
        return [e.to_dict() for e in expenses]


def delete_expense(expense_id: int) -> bool:
    """Deletes an expense by ID."""
    with get_session() as session:
        exp = session.query(Expense).filter(Expense.id == expense_id).first()
        if not exp:
            raise ValueError(f"Expense #{expense_id} not found.")
        session.delete(exp)
        session.commit()
        return True


def get_expense_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Returns expense summary grouped by category for a date range."""
    if start_date is None:
        start_date = date.today().replace(day=1)
    if end_date is None:
        end_date = date.today()

    with get_session() as session:
        results = (
            session.query(
                ExpenseCategory.name,
                func.count(Expense.id).label("count"),
                func.sum(Expense.total_amount).label("total")
            )
            .outerjoin(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
            .filter(Expense.expense_date >= start_date, Expense.expense_date <= end_date)
            .group_by(ExpenseCategory.name)
            .order_by(desc("total"))
            .all()
        )

        categories = []
        grand_total = Decimal("0.00")
        for cat_name, count, total in results:
            total_val = total or Decimal("0.00")
            categories.append({
                "category": cat_name or "Uncategorized",
                "count": count,
                "total": float(total_val)
            })
            grand_total += total_val

        # Monthly trend (last 6 months)
        monthly = []
        today = date.today()
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

            m_total = session.query(func.sum(Expense.total_amount)).filter(
                Expense.expense_date >= m_start,
                Expense.expense_date <= m_end
            ).scalar() or 0.0

            monthly.append({
                "month": m_start.strftime("%b %Y"),
                "month_short": m_start.strftime("%b"),
                "total": float(m_total)
            })

        return {
            "categories": categories,
            "grand_total": float(grand_total),
            "total_amount": float(grand_total),
            "expense_count": sum(c.get("count", 0) for c in categories),
            "monthly_trend": monthly,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }


# Aliases for compatibility
add_expense = create_expense
get_expenses_summary = get_expense_summary


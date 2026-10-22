"""
Profit & Loss Statement Business Logic Service
Auto-calculates P&L from vouchers (Sales = Debit vouchers, Purchases = Credit vouchers),
invoices, and expenses. Inspired by Vyapar's P&L and TallyPrime's Trading & P&L Account.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy import func

from app.database.connection import get_session
from app.database.models import (
    Voucher, Invoice, Expense, ExpenseCategory
)
from app.config import VOUCHER_DEBIT, VOUCHER_CREDIT


class ProfitAmount(float):
    """Float wrapper that allows dict-style key access ['amount'] for backwards compatibility."""
    @property
    def amount(self):
        return float(self)

    def __getitem__(self, item):
        if item == 'amount':
            return float(self)
        raise KeyError(item)

    def get(self, item, default=None):
        if item == 'amount':
            return float(self)
        return default


def get_profit_loss_statement(

    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Generates Profit & Loss statement for the given period.
    
    Revenue = Total of Debit vouchers (Sales) + Final invoices
    Cost of Goods = Total of Credit vouchers (Purchases)
    Gross Profit = Revenue - COGS
    Operating Expenses = Sum of all Expense entries by category
    Net Profit = Gross Profit - Operating Expenses
    """
    # Default to current financial year (April to March)
    if start_date is None:
        today = date.today()
        if today.month >= 4:
            start_date = date(today.year, 4, 1)
        else:
            start_date = date(today.year - 1, 4, 1)
    if end_date is None:
        end_date = date.today()

    with get_session() as session:
        # ────────────────────────────────────────────
        # REVENUE (Income)
        # ────────────────────────────────────────────
        # Sales from Debit Vouchers (accounting module)
        voucher_sales = session.query(func.sum(Voucher.total_amount)).filter(
            Voucher.voucher_type == VOUCHER_DEBIT,
            Voucher.voucher_date >= start_date,
            Voucher.voucher_date <= end_date
        ).scalar() or Decimal("0.00")

        # Sales from Tax Invoices (billing module)
        invoice_sales = session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
            Invoice.status != "cancelled"
        ).scalar() or Decimal("0.00")

        # Total Revenue (take the higher of voucher sales vs invoice sales to avoid double-counting)
        total_revenue = max(Decimal(str(voucher_sales)), Decimal(str(invoice_sales)))

        # Tax collected (from invoices or vouchers)
        voucher_tax = session.query(func.sum(Voucher.total_tax)).filter(
            Voucher.voucher_type == VOUCHER_DEBIT,
            Voucher.voucher_date >= start_date,
            Voucher.voucher_date <= end_date
        ).scalar() or Decimal("0.00")

        invoice_tax = session.query(func.sum(Invoice.tax_amount)).filter(
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
            Invoice.status != "cancelled"
        ).scalar() or Decimal("0.00")

        tax_collected = max(Decimal(str(voucher_tax)), Decimal(str(invoice_tax)))

        # ────────────────────────────────────────────
        # COST OF GOODS SOLD (Purchases)
        # ────────────────────────────────────────────
        voucher_purchases = session.query(func.sum(Voucher.total_amount)).filter(
            Voucher.voucher_type == VOUCHER_CREDIT,
            Voucher.voucher_date >= start_date,
            Voucher.voucher_date <= end_date
        ).scalar() or Decimal("0.00")

        cogs = Decimal(str(voucher_purchases))

        purchase_tax = session.query(func.sum(Voucher.total_tax)).filter(
            Voucher.voucher_type == VOUCHER_CREDIT,
            Voucher.voucher_date >= start_date,
            Voucher.voucher_date <= end_date
        ).scalar() or Decimal("0.00")

        tax_paid = Decimal(str(purchase_tax))

        # ────────────────────────────────────────────
        # GROSS PROFIT
        # ────────────────────────────────────────────
        gross_profit = total_revenue - cogs

        # ────────────────────────────────────────────
        # OPERATING EXPENSES (from Expense module)
        # ────────────────────────────────────────────
        expense_rows = (
            session.query(
                ExpenseCategory.name,
                func.sum(Expense.total_amount).label("total")
            )
            .outerjoin(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
            .filter(
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date
            )
            .group_by(ExpenseCategory.name)
            .order_by(func.sum(Expense.total_amount).desc())
            .all()
        )

        expense_breakdown = []
        total_expenses = Decimal("0.00")
        for cat_name, total in expense_rows:
            total_val = total or Decimal("0.00")
            expense_breakdown.append({
                "category": cat_name or "Uncategorized",
                "amount": float(total_val)
            })
            total_expenses += total_val

        # ────────────────────────────────────────────
        # NET PROFIT
        # ────────────────────────────────────────────
        net_profit = gross_profit - total_expenses

        # ────────────────────────────────────────────
        # Monthly breakdown for chart
        # ────────────────────────────────────────────
        monthly_data = []
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

            m_revenue = session.query(func.sum(Voucher.total_amount)).filter(
                Voucher.voucher_type == VOUCHER_DEBIT,
                Voucher.voucher_date >= m_start,
                Voucher.voucher_date <= m_end
            ).scalar() or 0.0

            m_cogs = session.query(func.sum(Voucher.total_amount)).filter(
                Voucher.voucher_type == VOUCHER_CREDIT,
                Voucher.voucher_date >= m_start,
                Voucher.voucher_date <= m_end
            ).scalar() or 0.0

            m_expenses = session.query(func.sum(Expense.total_amount)).filter(
                Expense.expense_date >= m_start,
                Expense.expense_date <= m_end
            ).scalar() or 0.0

            m_net = float(m_revenue) - float(m_cogs) - float(m_expenses)

            monthly_data.append({
                "month": m_start.strftime("%b %Y"),
                "month_short": m_start.strftime("%b"),
                "revenue": float(m_revenue),
                "cogs": float(m_cogs),
                "expenses": float(m_expenses),
                "net_profit": m_net
            })

        gp_val = ProfitAmount(float(gross_profit))
        np_val = ProfitAmount(float(net_profit))

        cogs_dict = {
            "total_purchases": float(cogs),
            "tax_paid": float(tax_paid),
            "total": float(cogs),
        }
        rev_dict = {
            "total_sales": float(total_revenue),
            "tax_collected": float(tax_collected),
            "total": float(total_revenue),
        }

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "revenue": rev_dict,
            "cost_of_goods": cogs_dict,
            "cogs": cogs_dict,
            "gross_profit": gp_val,
            "operating_expenses": {
                "breakdown": expense_breakdown,
                "total": float(total_expenses),
            },
            "net_profit": np_val,
            "gross_margin_pct": round(float(gross_profit) / float(total_revenue) * 100, 1) if total_revenue > 0 else 0.0,
            "net_margin_pct": round(float(net_profit) / float(total_revenue) * 100, 1) if total_revenue > 0 else 0.0,
            "monthly_trend": monthly_data,
        }


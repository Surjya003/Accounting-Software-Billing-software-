"""
Profit & Loss Statement Business Logic Service
Auto-calculates P&L from vouchers, invoices, inventory valuation, and expenses.
Inspired by Vyapar's P&L and TallyPrime's Trading & P&L Account.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy import func

from app.database.connection import get_session
from app.database.models import (
    Voucher, Invoice, InvoiceItem, Expense, ExpenseCategory,
    Product, SalesReturn, SalesReturnItem, PurchaseReturn, PurchaseReturnItem,
    PurchaseOrder, PurchaseOrderItem
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
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Dict[str, Any]:
    if start_date is None and from_date is not None:
        start_date = from_date
    if end_date is None and to_date is not None:
        end_date = to_date
    """
    Generates Profit & Loss statement for the given period.
    
    Revenue = Net Sales (sales minus sales returns, excluding GST).
    COGS = Opening Stock + Net Purchases (purchases minus purchase returns, excluding GST) - Closing Stock.
    Customer receipts, payments, GST, and contra/journal entries do NOT enter COGS.
    Operating Expenses = Sum of all Expense entries by category.
    Gross Profit = Revenue - COGS.
    Net Profit = Gross Profit - Operating Expenses.
    Stock valuation: current stock x latest purchase price.
    """
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
        # 1. REVENUE (Net Sales excluding GST)
        # ────────────────────────────────────────────
        inv_sales = session.query(func.coalesce(func.sum(Invoice.subtotal), Decimal("0.00"))).filter(
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
            Invoice.status == "final"
        ).scalar() or Decimal("0.00")

        vch_sales = session.query(func.coalesce(func.sum(Voucher.amount_untaxed), Decimal("0.00"))).filter(
            Voucher.voucher_type == VOUCHER_DEBIT,
            Voucher.voucher_date >= start_date,
            Voucher.voucher_date <= end_date,
            (Voucher.is_tax_invoice.is_(True) | Voucher.voucher_number.like("INV%"))
        ).scalar() or Decimal("0.00")

        gross_sales = max(Decimal(str(inv_sales)), Decimal(str(vch_sales)))

        # Sales returns (excluding GST)
        sr_amount = session.query(func.coalesce(func.sum(SalesReturn.subtotal), Decimal("0.00"))).filter(
            SalesReturn.return_date >= start_date,
            SalesReturn.return_date <= end_date,
            SalesReturn.status != "rejected"
        ).scalar() or Decimal("0.00")

        vch_sr = session.query(func.coalesce(func.sum(Voucher.amount_untaxed), Decimal("0.00"))).filter(
            Voucher.voucher_date >= start_date,
            Voucher.voucher_date <= end_date,
            Voucher.voucher_number.like("CN%")
        ).scalar() or Decimal("0.00")

        sales_returns = max(Decimal(str(sr_amount)), Decimal(str(vch_sr)))
        net_sales = max(Decimal("0.00"), gross_sales - sales_returns)

        # Tax collected (GST on sales)
        inv_tax = session.query(func.coalesce(func.sum(Invoice.tax_amount), Decimal("0.00"))).filter(
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
            Invoice.status == "final"
        ).scalar() or Decimal("0.00")
        tax_collected = Decimal(str(inv_tax))

        # ────────────────────────────────────────────
        # 2. PURCHASES (Net Purchases excluding GST)
        # ────────────────────────────────────────────
        pur_vch = session.query(func.coalesce(func.sum(Voucher.amount_untaxed), Decimal("0.00"))).filter(
            Voucher.voucher_date >= start_date,
            Voucher.voucher_date <= end_date,
            (Voucher.voucher_number.like("PUR%") | Voucher.narration.like("%Goods Receipt%"))
        ).scalar() or Decimal("0.00")

        # Purchase returns (excluding GST)
        pr_amount = session.query(func.coalesce(func.sum(PurchaseReturn.subtotal), Decimal("0.00"))).filter(
            PurchaseReturn.return_date >= start_date,
            PurchaseReturn.return_date <= end_date,
            PurchaseReturn.status != "rejected"
        ).scalar() or Decimal("0.00")

        vch_pr = session.query(func.coalesce(func.sum(Voucher.amount_untaxed), Decimal("0.00"))).filter(
            Voucher.voucher_date >= start_date,
            Voucher.voucher_date <= end_date,
            Voucher.voucher_number.like("DN%")
        ).scalar() or Decimal("0.00")

        purchase_returns = max(Decimal(str(pr_amount)), Decimal(str(vch_pr)))
        gross_purchases = Decimal(str(pur_vch))
        net_purchases = max(Decimal("0.00"), gross_purchases - purchase_returns)

        # Tax paid on purchases
        pur_tax = session.query(func.coalesce(func.sum(Voucher.total_tax), Decimal("0.00"))).filter(
            Voucher.voucher_date >= start_date,
            Voucher.voucher_date <= end_date,
            (Voucher.voucher_number.like("PUR%") | Voucher.narration.like("%Goods Receipt%"))
        ).scalar() or Decimal("0.00")
        tax_paid = Decimal(str(pur_tax))

        # ────────────────────────────────────────────
        # 3. STOCK VALUATION & COGS (Set-Based Unified Valuation Engine)
        # COGS = Opening Stock + Net Purchases - Closing Stock
        # ────────────────────────────────────────────
        from app.services.inventory_valuation import calculate_inventory_valuation
        val_res = calculate_inventory_valuation(session, start_date=start_date, end_date=end_date)
        total_opening_stock = val_res["total_opening_stock_value"]
        total_closing_stock = val_res["total_closing_stock_value"]
        valuation_method_display = val_res["method_display"]

        # COGS = Opening Stock + Net Purchases - Closing Stock
        calculated_cogs = total_opening_stock + net_purchases - total_closing_stock
        cogs = max(Decimal("0.00"), calculated_cogs)

        # ────────────────────────────────────────────
        # 4. GROSS PROFIT
        # ────────────────────────────────────────────
        gross_profit = net_sales - cogs

        # ────────────────────────────────────────────
        # 5. OPERATING EXPENSES (from Expense module)
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
            total_val = Decimal(str(total or "0.00"))
            expense_breakdown.append({
                "category": cat_name or "Uncategorized",
                "amount": float(total_val)
            })
            total_expenses += total_val

        # ────────────────────────────────────────────
        # 6. NET PROFIT
        # ────────────────────────────────────────────
        net_profit = gross_profit - total_expenses

        # ────────────────────────────────────────────
        # 7. Monthly breakdown for chart
        # ────────────────────────────────────────────
        today = date.today()
        monthly_data = []
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

            m_revenue = session.query(func.coalesce(func.sum(Invoice.subtotal), Decimal("0.00"))).filter(
                Invoice.status == "final",
                Invoice.invoice_date >= m_start,
                Invoice.invoice_date <= m_end
            ).scalar() or Decimal("0.00")

            m_cogs = session.query(func.coalesce(func.sum(Voucher.amount_untaxed), Decimal("0.00"))).filter(
                Voucher.voucher_date >= m_start,
                Voucher.voucher_date <= m_end,
                (Voucher.voucher_number.like("PUR%") | Voucher.narration.like("%Goods Receipt%"))
            ).scalar() or Decimal("0.00")

            m_exp = session.query(func.coalesce(func.sum(Expense.total_amount), Decimal("0.00"))).filter(
                Expense.expense_date >= m_start,
                Expense.expense_date <= m_end
            ).scalar() or Decimal("0.00")

            m_net = float(m_revenue) - float(m_cogs) - float(m_exp)

            monthly_data.append({
                "month": m_start.strftime("%b %Y"),
                "month_short": m_start.strftime("%b"),
                "revenue": float(m_revenue),
                "cogs": float(m_cogs),
                "expenses": float(m_exp),
                "net_profit": m_net
            })

        gp_val = ProfitAmount(float(gross_profit))
        np_val = ProfitAmount(float(net_profit))

        cogs_dict = {
            "total_purchases": float(cogs),
            "opening_stock": float(total_opening_stock),
            "net_purchases": float(net_purchases),
            "closing_stock": float(total_closing_stock),
            "tax_paid": float(tax_paid),
            "total": float(cogs),
            "valuation_method": valuation_method_display,
        }
        rev_dict = {
            "total_sales": float(net_sales),
            "gross_sales": float(gross_sales),
            "sales_returns": float(sales_returns),
            "tax_collected": float(tax_collected),
            "total": float(net_sales),
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
            "gross_margin_pct": round(float(gross_profit) / float(net_sales) * 100, 1) if net_sales > 0 else 0.0,
            "net_margin_pct": round(float(net_profit) / float(net_sales) * 100, 1) if net_sales > 0 else 0.0,
            "monthly_trend": monthly_data,
        }


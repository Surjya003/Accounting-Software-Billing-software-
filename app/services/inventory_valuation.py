"""
Inventory Valuation Service
Implements statutory stock valuation methodologies (Weighted Average Cost and FIFO)
per Indian Accounting Standard AS 2 / Ind AS 2 (Inventories).
Provides unified set-based SQL calculations used across P&L, Stock Summary, and Dashboard.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, List
from sqlalchemy import func

from app.database.models import (
    Product, Invoice, InvoiceItem, PurchaseOrder, PurchaseOrderItem,
    SalesReturn, SalesReturnItem, PurchaseReturn, PurchaseReturnItem,
    CompanyProfile
)

VALUATION_METHOD_WAC = "weighted_average"
VALUATION_METHOD_FIFO = "fifo"

DEFAULT_VALUATION_METHOD = VALUATION_METHOD_WAC
VALUATION_DISPLAY_NAMES = {
    VALUATION_METHOD_WAC: "Weighted Average Cost (WAC)",
    VALUATION_METHOD_FIFO: "First-In, First-Out (FIFO)",
}


def get_configured_valuation_method(session) -> str:
    """Returns the configured stock valuation method from CompanyProfile or default."""
    try:
        profile = session.query(CompanyProfile).first()
        if profile and getattr(profile, "stock_valuation_method", None):
            method = profile.stock_valuation_method.lower().strip()
            if method in (VALUATION_METHOD_WAC, VALUATION_METHOD_FIFO):
                return method
    except Exception:
        pass
    return DEFAULT_VALUATION_METHOD


def calculate_inventory_valuation(
    session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    product_ids: Optional[List[int]] = None,
    method: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes set-based inventory valuation for all or specified active products.
    Uses bulk GROUP BY SQL queries (zero N+1 queries) for maximum performance.
    
    Returns:
        dict containing:
            - method: valuation method used ("weighted_average" or "fifo")
            - method_display: human-readable name for UI and reports
            - products: dict mapping product_id to valuation details
            - total_opening_stock_value: Decimal
            - total_closing_stock_value: Decimal
            - total_cogs: Decimal
            - total_units_closing: Decimal
    """
    today = date.today()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = date(end_date.year if end_date.month >= 4 else end_date.year - 1, 4, 1)

    if not method:
        method = get_configured_valuation_method(session)

    # 1. Fetch products
    prod_query = session.query(Product).filter(Product.is_active.is_(True))
    if product_ids:
        prod_query = prod_query.filter(Product.id.in_(product_ids))
    products = prod_query.all()

    if not products:
        return {
            "method": method,
            "method_display": VALUATION_DISPLAY_NAMES.get(method, "Weighted Average Cost (WAC)"),
            "products": {},
            "total_opening_stock_value": Decimal("0.00"),
            "total_closing_stock_value": Decimal("0.00"),
            "total_cogs": Decimal("0.00"),
            "total_units_closing": Decimal("0.000"),
        }

    # 2. Cumulative inward receipts up to end_date (PO received)
    po_q = (
        session.query(
            PurchaseOrderItem.product_id,
            func.sum(func.coalesce(func.nullif(PurchaseOrderItem.received_quantity, 0), PurchaseOrderItem.quantity)).label("total_qty"),
            func.sum(
                func.coalesce(func.nullif(PurchaseOrderItem.received_quantity, 0), PurchaseOrderItem.quantity) * PurchaseOrderItem.unit_price
            ).label("total_cost")
        )
        .join(PurchaseOrder, PurchaseOrderItem.po_id == PurchaseOrder.id)
        .filter(
            PurchaseOrder.po_date <= end_date,
            PurchaseOrder.status.in_(["received", "partially_received", "completed"])
        )
    )
    if product_ids:
        po_q = po_q.filter(PurchaseOrderItem.product_id.in_(product_ids))
    po_rows = po_q.group_by(PurchaseOrderItem.product_id).all()
    po_map = {
        r.product_id: (Decimal(str(r.total_qty or 0)), Decimal(str(r.total_cost or 0)))
        for r in po_rows
    }

    # 3. Cumulative purchase returns up to end_date
    pr_q = (
        session.query(
            PurchaseReturnItem.product_id,
            func.sum(PurchaseReturnItem.quantity).label("total_qty"),
            func.sum(PurchaseReturnItem.quantity * PurchaseReturnItem.unit_price).label("total_cost")
        )
        .join(PurchaseReturn, PurchaseReturnItem.return_id == PurchaseReturn.id)
        .filter(
            PurchaseReturn.return_date <= end_date,
            PurchaseReturn.status != "rejected"
        )
    )
    if product_ids:
        pr_q = pr_q.filter(PurchaseReturnItem.product_id.in_(product_ids))
    pr_rows = pr_q.group_by(PurchaseReturnItem.product_id).all()
    pr_map = {
        r.product_id: (Decimal(str(r.total_qty or 0)), Decimal(str(r.total_cost or 0)))
        for r in pr_rows
    }

    # 4. Post-end date movements (needed only if end_date < today)
    post_sold_map = {}
    post_sr_map = {}
    post_po_map = {}
    post_pr_map = {}

    if end_date < today:
        inv_post = (
            session.query(InvoiceItem.product_id, func.sum(InvoiceItem.quantity).label("qty"))
            .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
            .filter(Invoice.invoice_date > end_date, Invoice.status == "final")
        )
        if product_ids:
            inv_post = inv_post.filter(InvoiceItem.product_id.in_(product_ids))
        post_sold_map = {r.product_id: Decimal(str(r.qty or 0)) for r in inv_post.group_by(InvoiceItem.product_id).all()}

        sr_post = (
            session.query(SalesReturnItem.product_id, func.sum(SalesReturnItem.quantity).label("qty"))
            .join(SalesReturn, SalesReturnItem.return_id == SalesReturn.id)
            .filter(SalesReturn.return_date > end_date, SalesReturn.status != "rejected")
        )
        if product_ids:
            sr_post = sr_post.filter(SalesReturnItem.product_id.in_(product_ids))
        post_sr_map = {r.product_id: Decimal(str(r.qty or 0)) for r in sr_post.group_by(SalesReturnItem.product_id).all()}

        po_post = (
            session.query(
                PurchaseOrderItem.product_id,
                func.sum(func.coalesce(func.nullif(PurchaseOrderItem.received_quantity, 0), PurchaseOrderItem.quantity)).label("qty")
            )
            .join(PurchaseOrder, PurchaseOrderItem.po_id == PurchaseOrder.id)
            .filter(PurchaseOrder.po_date > end_date, PurchaseOrder.status.in_(["received", "partially_received", "completed"]))
        )
        if product_ids:
            po_post = po_post.filter(PurchaseOrderItem.product_id.in_(product_ids))
        post_po_map = {r.product_id: Decimal(str(r.qty or 0)) for r in po_post.group_by(PurchaseOrderItem.product_id).all()}

        pr_post = (
            session.query(PurchaseReturnItem.product_id, func.sum(PurchaseReturnItem.quantity).label("qty"))
            .join(PurchaseReturn, PurchaseReturnItem.return_id == PurchaseReturn.id)
            .filter(PurchaseReturn.return_date > end_date, PurchaseReturn.status != "rejected")
        )
        if product_ids:
            pr_post = pr_post.filter(PurchaseReturnItem.product_id.in_(product_ids))
        post_pr_map = {r.product_id: Decimal(str(r.qty or 0)) for r in pr_post.group_by(PurchaseReturnItem.product_id).all()}

    # 5. Period movements between start_date and end_date
    inv_period = (
        session.query(InvoiceItem.product_id, func.sum(InvoiceItem.quantity).label("qty"))
        .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
        .filter(Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date, Invoice.status == "final")
    )
    if product_ids:
        inv_period = inv_period.filter(InvoiceItem.product_id.in_(product_ids))
    period_sold_map = {r.product_id: Decimal(str(r.qty or 0)) for r in inv_period.group_by(InvoiceItem.product_id).all()}

    sr_period = (
        session.query(SalesReturnItem.product_id, func.sum(SalesReturnItem.quantity).label("qty"))
        .join(SalesReturn, SalesReturnItem.return_id == SalesReturn.id)
        .filter(SalesReturn.return_date >= start_date, SalesReturn.return_date <= end_date, SalesReturn.status != "rejected")
    )
    if product_ids:
        sr_period = sr_period.filter(SalesReturnItem.product_id.in_(product_ids))
    period_sr_map = {r.product_id: Decimal(str(r.qty or 0)) for r in sr_period.group_by(SalesReturnItem.product_id).all()}

    po_period = (
        session.query(
            PurchaseOrderItem.product_id,
            func.sum(func.coalesce(func.nullif(PurchaseOrderItem.received_quantity, 0), PurchaseOrderItem.quantity)).label("qty"),
            func.sum(
                func.coalesce(func.nullif(PurchaseOrderItem.received_quantity, 0), PurchaseOrderItem.quantity) * PurchaseOrderItem.unit_price
            ).label("cost")
        )
        .join(PurchaseOrder, PurchaseOrderItem.po_id == PurchaseOrder.id)
        .filter(
            PurchaseOrder.po_date >= start_date,
            PurchaseOrder.po_date <= end_date,
            PurchaseOrder.status.in_(["received", "partially_received", "completed"])
        )
    )
    if product_ids:
        po_period = po_period.filter(PurchaseOrderItem.product_id.in_(product_ids))
    period_po_map = {
        r.product_id: (Decimal(str(r.qty or 0)), Decimal(str(r.cost or 0)))
        for r in po_period.group_by(PurchaseOrderItem.product_id).all()
    }

    pr_period = (
        session.query(
            PurchaseReturnItem.product_id,
            func.sum(PurchaseReturnItem.quantity).label("qty"),
            func.sum(PurchaseReturnItem.quantity * PurchaseReturnItem.unit_price).label("cost")
        )
        .join(PurchaseReturn, PurchaseReturnItem.return_id == PurchaseReturn.id)
        .filter(
            PurchaseReturn.return_date >= start_date,
            PurchaseReturn.return_date <= end_date,
            PurchaseReturn.status != "rejected"
        )
    )
    if product_ids:
        pr_period = pr_period.filter(PurchaseReturnItem.product_id.in_(product_ids))
    period_pr_map = {
        r.product_id: (Decimal(str(r.qty or 0)), Decimal(str(r.cost or 0)))
        for r in pr_period.group_by(PurchaseReturnItem.product_id).all()
    }

    # 6. Compute per-product valuation using Weighted Average Cost
    product_results = {}
    total_opening_stock_value = Decimal("0.00")
    total_closing_stock_value = Decimal("0.00")
    total_cogs = Decimal("0.00")
    total_units_closing = Decimal("0.000")

    for prod in products:
        pid = prod.id
        curr_stock = Decimal(str(prod.stock_quantity or "0.000"))
        default_cost = Decimal(str(prod.purchase_price or prod.price or "0.00"))

        # Inward purchases & returns up to end_date
        cum_po_qty, cum_po_cost = po_map.get(pid, (Decimal("0.000"), Decimal("0.00")))
        cum_pr_qty, cum_pr_cost = pr_map.get(pid, (Decimal("0.000"), Decimal("0.00")))
        net_inward_qty = cum_po_qty - cum_pr_qty
        net_inward_cost = cum_po_cost - cum_pr_cost

        # Weighted Average Cost calculation
        if net_inward_qty > Decimal("0.000") and net_inward_cost > Decimal("0.00"):
            wac_cost = (net_inward_cost / net_inward_qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            wac_cost = default_cost

        # Closing stock at end_date
        if end_date < today:
            post_sold = post_sold_map.get(pid, Decimal("0.000"))
            post_sr = post_sr_map.get(pid, Decimal("0.000"))
            post_po = post_po_map.get(pid, Decimal("0.000"))
            post_pr = post_pr_map.get(pid, Decimal("0.000"))
            stock_at_end = curr_stock + post_sold - post_sr - post_po + post_pr
        else:
            stock_at_end = curr_stock

        stock_at_end = max(Decimal("0.000"), stock_at_end)

        # Period movements
        p_sold = period_sold_map.get(pid, Decimal("0.000"))
        p_sr = period_sr_map.get(pid, Decimal("0.000"))
        p_po_qty, p_po_cost = period_po_map.get(pid, (Decimal("0.000"), Decimal("0.00")))
        p_pr_qty, p_pr_cost = period_pr_map.get(pid, (Decimal("0.000"), Decimal("0.00")))

        net_added_in_period = (p_po_qty - p_pr_qty) - (p_sold - p_sr)
        stock_at_start = max(Decimal("0.000"), stock_at_end - net_added_in_period)

        opening_val = (stock_at_start * wac_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        closing_val = (stock_at_end * wac_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        net_sold_qty = max(Decimal("0.000"), p_sold - p_sr)
        prod_cogs = (net_sold_qty * wac_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        product_results[pid] = {
            "product_id": pid,
            "product_name": prod.name,
            "unit_cost": float(wac_cost),
            "stock_at_start": float(stock_at_start),
            "stock_at_end": float(stock_at_end),
            "opening_value": float(opening_val),
            "closing_value": float(closing_val),
            "period_sold_qty": float(p_sold),
            "period_sr_qty": float(p_sr),
            "period_received_qty": float(p_po_qty),
            "period_pr_qty": float(p_pr_qty),
            "cogs": float(prod_cogs)
        }

        total_opening_stock_value += opening_val
        total_closing_stock_value += closing_val
        total_cogs += prod_cogs
        total_units_closing += stock_at_end

    return {
        "method": method,
        "method_display": VALUATION_DISPLAY_NAMES.get(method, "Weighted Average Cost (WAC)"),
        "products": product_results,
        "total_opening_stock_value": total_opening_stock_value,
        "total_closing_stock_value": total_closing_stock_value,
        "total_cogs": total_cogs,
        "total_units_closing": total_units_closing,
    }

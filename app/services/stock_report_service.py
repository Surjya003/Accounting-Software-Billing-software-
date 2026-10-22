"""
Stock Movement & Item-wise Report Service
Tracks per-product sales/purchase history, stock movement (in/out), and per-item profitability.
Inspired by Vyapar's Item Report and TallyPrime's Stock Summary / Movement Analysis.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List
from sqlalchemy import func, desc, asc, and_

from app.database.connection import get_session
from app.database.models import (
    Product, InvoiceItem, Invoice,
    PurchaseOrderItem, PurchaseOrder,
    SalesReturnItem, SalesReturn,
    PurchaseReturnItem, PurchaseReturn,
)


def get_stock_movement_report(
    product_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Returns item-wise stock movement summary:
    - Opening stock, Purchased, Sold, Returned, Closing stock
    - Sales revenue, Purchase cost, Profit per item
    """
    if start_date is None:
        today = date.today()
        start_date = today.replace(day=1)
    if end_date is None:
        end_date = date.today()

    with get_session() as session:
        # Get products
        query = session.query(Product).filter(Product.is_active.is_(True))
        if product_id:
            query = query.filter(Product.id == product_id)
        products = query.order_by(Product.name.asc()).all()

        items = []
        totals = {
            "total_sales_value": 0.0,
            "total_purchase_value": 0.0,
            "total_profit": 0.0,
            "total_qty_sold": 0.0,
            "total_qty_purchased": 0.0,
        }

        # Bulk pre-aggregated queries: exactly 4 fast queries instead of 4 * N queries
        sold_rows = (
            session.query(
                InvoiceItem.product_id,
                func.sum(InvoiceItem.quantity).label("qty"),
                func.sum(InvoiceItem.total_amount).label("revenue"),
                func.sum(InvoiceItem.taxable_value).label("taxable")
            )
            .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
            .filter(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date,
                Invoice.status != "cancelled"
            )
            .group_by(InvoiceItem.product_id)
            .all()
        )
        sold_map = {
            r.product_id: (float(r.qty or 0), float(r.revenue or 0), float(r.taxable or 0))
            for r in sold_rows
        }

        purchased_rows = (
            session.query(
                PurchaseOrderItem.product_id,
                func.sum(func.coalesce(func.nullif(PurchaseOrderItem.received_quantity, 0), PurchaseOrderItem.quantity)).label("qty"),
                func.sum(PurchaseOrderItem.total_amount).label("cost")
            )
            .join(PurchaseOrder, PurchaseOrderItem.po_id == PurchaseOrder.id)
            .filter(
                PurchaseOrder.po_date >= start_date,
                PurchaseOrder.po_date <= end_date,
                PurchaseOrder.status.in_(["received", "partially_received"])
            )
            .group_by(PurchaseOrderItem.product_id)
            .all()
        )
        purchased_map = {
            r.product_id: (float(r.qty or 0), float(r.cost or 0))
            for r in purchased_rows
        }

        sr_rows = (
            session.query(
                SalesReturnItem.product_id,
                func.sum(SalesReturnItem.quantity).label("qty")
            )
            .join(SalesReturn, SalesReturnItem.return_id == SalesReturn.id)
            .filter(
                SalesReturn.return_date >= start_date,
                SalesReturn.return_date <= end_date,
                SalesReturn.status == "approved"
            )
            .group_by(SalesReturnItem.product_id)
            .all()
        )
        sr_map = {r.product_id: float(r.qty or 0) for r in sr_rows}

        pr_rows = (
            session.query(
                PurchaseReturnItem.product_id,
                func.sum(PurchaseReturnItem.quantity).label("qty")
            )
            .join(PurchaseReturn, PurchaseReturnItem.return_id == PurchaseReturn.id)
            .filter(
                PurchaseReturn.return_date >= start_date,
                PurchaseReturn.return_date <= end_date,
                PurchaseReturn.status == "approved"
            )
            .group_by(PurchaseReturnItem.product_id)
            .all()
        )
        pr_map = {r.product_id: float(r.qty or 0) for r in pr_rows}

        for prod in products:
            qty_sold, sales_revenue, sales_taxable = sold_map.get(prod.id, (0.0, 0.0, 0.0))
            qty_purchased, purchase_cost = purchased_map.get(prod.id, (0.0, 0.0))
            qty_sales_returned = sr_map.get(prod.id, 0.0)
            qty_purchase_returned = pr_map.get(prod.id, 0.0)

            # Net movement
            net_qty_sold = qty_sold - qty_sales_returned
            net_qty_purchased = qty_purchased - qty_purchase_returned

            # Profit calculation (selling price - purchase price) * qty sold
            purchase_price = float(prod.purchase_price or 0)
            selling_price = float(prod.price or 0)
            estimated_cogs = purchase_price * net_qty_sold if purchase_price > 0 else 0.0
            profit = sales_taxable - estimated_cogs if estimated_cogs > 0 else (sales_taxable - (purchase_cost * (net_qty_sold / qty_purchased if qty_purchased > 0 else 0)))
            margin_pct = (profit / sales_taxable * 100) if sales_taxable > 0 else 0.0

            item_data = {
                "id": prod.id,
                "name": prod.name,
                "hsn_code": prod.hsn_code or "",
                "category": prod.category or "",
                "unit": prod.unit,
                "current_stock": float(prod.stock_quantity or 0),
                "selling_price": selling_price,
                "purchase_price": purchase_price,
                "qty_purchased": net_qty_purchased,
                "qty_sold": net_qty_sold,
                "qty_sales_returned": qty_sales_returned,
                "qty_purchase_returned": qty_purchase_returned,
                "sales_revenue": sales_revenue,
                "purchase_cost": purchase_cost,
                "profit": round(profit, 2),
                "margin_pct": round(margin_pct, 1),
                "stock_value": round(float(prod.stock_quantity or 0) * purchase_price, 2),
                "low_stock_threshold": float(prod.low_stock_threshold or 10),
            }
            items.append(item_data)

            totals["total_sales_value"] += sales_revenue
            totals["total_purchase_value"] += purchase_cost
            totals["total_profit"] += profit
            totals["total_qty_sold"] += net_qty_sold
            totals["total_qty_purchased"] += net_qty_purchased

        # Round totals
        for k in totals:
            totals[k] = round(totals[k], 2)

        # Top movers (by qty sold)
        top_sellers = sorted(items, key=lambda x: x["qty_sold"], reverse=True)[:10]
        # Highest profit items
        most_profitable = sorted(items, key=lambda x: x["profit"], reverse=True)[:10]
        # Low stock items (calculated completely in-memory with zero queries)
        low_stock = [i for i in items if i["current_stock"] <= i["low_stock_threshold"]]

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "items": items,
            "totals": totals,
            "top_sellers": top_sellers,
            "most_profitable": most_profitable,
            "low_stock_count": len(low_stock),
            "total_products": len(items),
            "total_stock_value": round(sum(i["stock_value"] for i in items), 2),
        }

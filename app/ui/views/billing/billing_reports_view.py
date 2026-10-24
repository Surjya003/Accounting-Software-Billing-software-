"""
Billing Reports View — Overview of billing-related KPIs and statistics.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QPushButton
)
from PySide6.QtCore import Qt

from app.services.billing import (
    invoice_service, product_service, proforma_service,
    purchase_order_service, challan_service, return_service
)
from app.ui.theme import theme_manager
from app.ui.theme.widgets import PageHeaderWidget
from app.ui.widgets.stat_card import StatCard


class BillingReportsView(QWidget):
    """Billing-specific reports and KPI dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        self.header_widget = PageHeaderWidget(
            title="Billing Reports",
            subtitle="Overview of billing metrics, document counts, and inventory status"
        )
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_refresh.setProperty("variant", "secondary")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.refresh_data)
        self.header_widget.add_custom_action(btn_refresh)
        layout.addWidget(self.header_widget)

        # KPI Cards Grid
        grid = QGridLayout()
        grid.setSpacing(16)

        self.card_today = StatCard("TODAY'S SALES", "₹0", "Cash & credit billed", token_name="accent")
        self.card_month = StatCard("MONTHLY REVENUE", "₹0", "Current month sales", token_name="success")
        self.card_stock = StatCard("LOW STOCK ITEMS", "0", "Below reorder level", token_name="danger")
        self.card_returns = StatCard("PENDING RETURNS", "0", "Awaiting approval", token_name="warning")

        grid.addWidget(self.card_today, 0, 0)
        grid.addWidget(self.card_month, 0, 1)
        grid.addWidget(self.card_stock, 0, 2)
        grid.addWidget(self.card_returns, 0, 3)

        self.card_invoices = StatCard("TOTAL INVOICES", "0", "Cumulative invoices", token_name="info")
        self.card_proformas = StatCard("PROFORMAS", "0", "Quotations & estimates", token_name="accent")
        self.card_pos = StatCard("PURCHASE ORDERS", "0", "Issued to vendors", token_name="warning")
        self.card_challans = StatCard("DELIVERY CHALLANS", "0", "Goods in dispatch", token_name="success")

        grid.addWidget(self.card_invoices, 1, 0)
        grid.addWidget(self.card_proformas, 1, 1)
        grid.addWidget(self.card_pos, 1, 2)
        grid.addWidget(self.card_challans, 1, 3)

        layout.addLayout(grid)
        layout.addStretch()

        self.refresh_data()

    def refresh_data(self):
        try:
            self.card_today.set_value(f"₹{invoice_service.get_today_sales_total():,.0f}")
            self.card_month.set_value(f"₹{invoice_service.get_month_sales_total():,.0f}")
            self.card_stock.set_value(str(product_service.get_low_stock_count()))
            self.card_returns.set_value(str(return_service.get_pending_returns_count()))
            self.card_invoices.set_value(f"{invoice_service.get_invoice_count():,}")
            self.card_proformas.set_value(f"{proforma_service.get_proforma_count():,}")
            self.card_pos.set_value(f"{purchase_order_service.get_po_count():,}")
            self.card_challans.set_value(f"{challan_service.get_challan_count():,}")
        except Exception as e:
            print(f"Billing Reports Error: {e}")

"""
Billing Reports View — Overview of billing-related KPIs and statistics.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.services.billing import (
    invoice_service, product_service, proforma_service,
    purchase_order_service, challan_service, return_service
)


class BillingReportsView(QWidget):
    """Billing-specific reports and KPI dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        tb = QVBoxLayout(); tb.setSpacing(4)
        lbl = QLabel("Billing Reports")
        lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")
        tb.addWidget(lbl)
        ls = QLabel("Overview of billing metrics, document counts, and inventory status")
        ls.setStyleSheet("font-size: 12px; color: #6B6558;")
        tb.addWidget(ls)
        layout.addLayout(tb)

        # KPI Cards
        grid = QGridLayout()
        grid.setSpacing(16)

        self.card_today = self._card("Today's Sales", "₹0", "#2C3E63")
        self.card_month = self._card("Monthly Revenue", "₹0", "#2F6844")
        self.card_stock = self._card("Low Stock Items", "0", "#8B2635")
        self.card_returns = self._card("Pending Returns", "0", "#A6822E")

        grid.addWidget(self.card_today, 0, 0)
        grid.addWidget(self.card_month, 0, 1)
        grid.addWidget(self.card_stock, 0, 2)
        grid.addWidget(self.card_returns, 0, 3)

        self.card_invoices = self._card("Total Invoices", "0", "#2C3E63")
        self.card_proformas = self._card("Proformas", "0", "#7D5A8F")
        self.card_pos = self._card("Purchase Orders", "0", "#A6822E")
        self.card_challans = self._card("Delivery Challans", "0", "#3F7A56")

        grid.addWidget(self.card_invoices, 1, 0)
        grid.addWidget(self.card_proformas, 1, 1)
        grid.addWidget(self.card_pos, 1, 2)
        grid.addWidget(self.card_challans, 1, 3)

        layout.addLayout(grid)
        layout.addStretch()

        self.refresh_data()

    def _card(self, title, value, color):
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(f"""
            #Card {{
                border-left: 5px solid {color};
                min-height: 90px;
            }}
        """)
        cl = QVBoxLayout(card); cl.setContentsMargins(16, 14, 16, 14); cl.setSpacing(6)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #6B6558; text-transform: uppercase;")
        cl.addWidget(lbl_title)

        lbl_value = QLabel(value)
        lbl_value.setObjectName("kpi_value")
        lbl_value.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color}; font-family: Consolas;")
        cl.addWidget(lbl_value)

        return card

    def _set_card_value(self, card, value):
        lbl = card.findChild(QLabel, "kpi_value")
        if lbl: lbl.setText(value)

    def refresh_data(self):
        try:
            self._set_card_value(self.card_today, f"₹{invoice_service.get_today_sales_total():,.0f}")
            self._set_card_value(self.card_month, f"₹{invoice_service.get_month_sales_total():,.0f}")
            self._set_card_value(self.card_stock, str(product_service.get_low_stock_count()))
            self._set_card_value(self.card_returns, str(return_service.get_pending_returns_count()))
            self._set_card_value(self.card_invoices, f"{invoice_service.get_invoice_count():,}")
            self._set_card_value(self.card_proformas, f"{proforma_service.get_proforma_count():,}")
            self._set_card_value(self.card_pos, f"{purchase_order_service.get_po_count():,}")
            self._set_card_value(self.card_challans, f"{challan_service.get_challan_count():,}")
        except Exception as e:
            print(f"Billing Reports Error: {e}")

"""
Views package init
"""
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.party_view import PartyView
from app.ui.views.voucher_view import VoucherEntryView
from app.ui.views.ledger_view import LedgerView
from app.ui.views.outstanding_view import OutstandingView
from app.ui.views.daybook_view import DayBookView
from app.ui.views.trial_balance_view import TrialBalanceView
from app.ui.views.gst_report_view import GSTReportView
from app.ui.views.settings_view import SettingsView

from app.ui.views.expense_view import ExpenseView
from app.ui.views.cashbank_view import CashBankView
from app.ui.views.pnl_view import PnLView
from app.ui.views.stock_report_view import StockReportView

from app.ui.views.billing.product_view import ProductView
from app.ui.views.billing.invoice_view import InvoiceView
from app.ui.views.billing.proforma_view import ProformaView
from app.ui.views.billing.quotation_view import QuotationView
from app.ui.views.billing.purchase_order_view import PurchaseOrderView
from app.ui.views.billing.challan_view import ChallanView
from app.ui.views.billing.return_view import ReturnView
from app.ui.views.billing.billing_reports_view import BillingReportsView


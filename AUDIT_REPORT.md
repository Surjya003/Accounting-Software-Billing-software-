# AUDIT REPORT: BILLFLOW SUITE UI/UX & STYLING
## 1. Inventory of Windows, Views, Dialogs, and Custom Widgets

### app/ui/main_window.py
- `MainWindow` (QMainWindow) - line 30

### app/ui/views/billing/billing_reports_view.py
- `BillingReportsView` (QWidget) - line 16

### app/ui/views/billing/challan_view.py
- `ChallanFormDialog` (QDialog) - line 23
- `ChallanView` (QWidget) - line 364

### app/ui/views/billing/invoice_view.py
- `InvoiceItemWidget` (QFrame) - line 20
- `InvoiceFormDialog` (QDialog) - line 153
- `InvoiceView` (QWidget) - line 538

### app/ui/views/billing/product_view.py
- `ProductDialog` (QDialog) - line 30
- `ProductView` (QWidget) - line 150

### app/ui/views/billing/proforma_view.py
- `ProformaFormDialog` (QDialog) - line 23
- `ProformaView` (QWidget) - line 406

### app/ui/views/billing/purchase_order_view.py
- `POFormDialog` (QDialog) - line 19
- `PurchaseOrderView` (QWidget) - line 112

### app/ui/views/billing/quotation_view.py
- `QuotationItemWidget` (QFrame) - line 26
- `QuotationFormDialog` (QDialog) - line 164
- `QuotationView` (QWidget) - line 588

### app/ui/views/billing/return_view.py
- `ReturnItemRow` (QFrame) - line 18
- `ReturnFormDialog` (QDialog) - line 49
- `ReturnView` (QWidget) - line 102

### app/ui/views/cashbank_view.py
- `CashBankView` (QWidget) - line 24
- `AddAccountDialog` (QDialog) - line 339
- `AddTransactionDialog` (QDialog) - line 398

### app/ui/views/dashboard_view.py
- `MonthlyTrendChart` (QWidget) - line 17
- `DashboardView` (QWidget) - line 121

### app/ui/views/daybook_view.py
- `DayBookView` (QWidget) - line 19

### app/ui/views/expense_view.py
- `ExpenseView` (QWidget) - line 24
- `AddExpenseDialog` (QDialog) - line 230
- `CategoryManagerDialog` (QDialog) - line 310

### app/ui/views/gst_report_view.py
- `GSTTabWidget` (QWidget) - line 20
- `GSTReportView` (QWidget) - line 208

### app/ui/views/ledger_view.py
- `LedgerView` (QWidget) - line 20

### app/ui/views/outstanding_view.py
- `OutstandingTabWidget` (QWidget) - line 25
- `OutstandingView` (QWidget) - line 247
- `WhatsAppReminderDialog` (QDialog) - line 273

### app/ui/views/party_view.py
- `PartyDialog` (QDialog) - line 21
- `PartyView` (QWidget) - line 230

### app/ui/views/pnl_view.py
- `PnLBarChart` (QWidget) - line 20
- `ProfitLossView` (QWidget) - line 108

### app/ui/views/settings_view.py
- `SettingsView` (QWidget) - line 23

### app/ui/views/stock_report_view.py
- `StockReportView` (QWidget) - line 23

### app/ui/views/trial_balance_view.py
- `TrialBalanceView` (QWidget) - line 17

### app/ui/views/voucher_view.py
- `VoucherEntryView` (QWidget) - line 28

### app/ui/widgets/party_combo.py
- `PartyComboBox` (QComboBox) - line 10

### app/ui/widgets/stat_card.py
- `StatCard` (QFrame) - line 9

## 2. Inline Stylesheet Calls (`setStyleSheet`)

### app/ui/main_window.py (6 calls)
- Line 43: `self.setStyleSheet(LIGHT_THEME)`
- Line 87: `section_bill.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 8px 8px 4px 8px;")`
- Line 116: `section_acct.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")`
- Line 145: `section_sys.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")`
- Line 161: `self.lbl_lic_badge.setStyleSheet("color: #D4C49E; font-size: 11px; font-weight: 600; padding: 6px;")`
- Line 193: `self.lbl_clock.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569; background-color: #F1F5F9; padding: 4px 10px; border-radius: 4px;")`

### app/ui/views/billing/billing_reports_view.py (5 calls)
- Line 31: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 34: `ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 70: `card.setStyleSheet(f"""`
- Line 79: `lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 84: `lbl_value.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color}; font-family: Consolas;")`

### app/ui/views/billing/challan_view.py (9 calls)
- Line 58: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 133: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 147: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 165: `scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")`
- Line 182: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas; padding: 4px 12px;")`
- Line 184: `lbl.setStyleSheet("font-family: Consolas; font-size: 13px; padding: 4px 12px;")`
- Line 374: `lbl = QLabel("Delivery Challans"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 376: `ls = QLabel("Create and track delivery challans"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 398: `self.lbl_count.setStyleSheet("color: #6B6558;")`

### app/ui/views/billing/invoice_view.py (12 calls)
- Line 28: `self.setStyleSheet("""`
- Line 83: `self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px;")`
- Line 90: `btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px;")`
- Line 193: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 290: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 304: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 323: `scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")`
- Line 338: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63;")`
- Line 340: `lbl.setStyleSheet(lbl.styleSheet() + "font-family: Consolas; padding: 4px 12px;")`
- Line 556: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 559: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 617: `self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")`

### app/ui/views/billing/product_view.py (4 calls)
- Line 47: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 168: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 171: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 254: `self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")`

### app/ui/views/billing/proforma_view.py (9 calls)
- Line 62: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 159: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 173: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 191: `scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")`
- Line 206: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63;")`
- Line 208: `lbl.setStyleSheet(lbl.styleSheet() + "font-family: Consolas; padding: 4px 12px;")`
- Line 424: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 427: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 474: `self.lbl_count.setStyleSheet("color: #6B6558;")`

### app/ui/views/billing/purchase_order_view.py (6 calls)
- Line 33: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;"); layout.addWidget(title)`
- Line 53: `lbl_items = QLabel("Items"); lbl_items.setStyleSheet("font-size: 15px; font-weight: 600;")`
- Line 63: `self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas;")`
- Line 122: `lbl = QLabel("Purchase Orders"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 124: `ls = QLabel("Create and track purchase orders to suppliers"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 147: `self.lbl_count = QLabel("0 orders"); self.lbl_count.setStyleSheet("color: #6B6558;")`

### app/ui/views/billing/quotation_view.py (14 calls)
- Line 34: `self.setStyleSheet("""`
- Line 94: `self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px; color: #1B1B18;")`
- Line 101: `btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px; background: transparent;")`
- Line 187: `lbl_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 192: `tabs.setStyleSheet("""`
- Line 309: `scroll.setStyleSheet("QScrollArea { border: 1px solid #D4C49E; background: #FFFFFF; border-radius: 4px; }")`
- Line 400: `summary_frame.setStyleSheet("background-color: #F7F5EE; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px 16px;")`
- Line 405: `self.lbl_subtotal.setStyleSheet("font-family: Consolas; font-weight: 600; color: #1B1B18;")`
- Line 410: `self.lbl_tax.setStyleSheet("font-family: Consolas; font-weight: 600; color: #2C3E63;")`
- Line 415: `self.lbl_grand_total.setStyleSheet("font-family: Consolas; font-size: 15px; font-weight: bold; color: #2F6844;")`
- Line 606: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 609: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 644: `filter_frame.setStyleSheet("""`
- Line 693: `self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")`

### app/ui/views/billing/return_view.py (4 calls)
- Line 62: `title.setStyleSheet("font-size: 18px; font-weight: 600;"); layout.addWidget(title)`
- Line 112: `lbl = QLabel("Returns"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 114: `ls = QLabel("Manage sales returns & purchase returns"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 132: `self.lbl_count = QLabel(""); self.lbl_count.setStyleSheet("color: #6B6558;")`

### app/ui/views/cashbank_view.py (4 calls)
- Line 39: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 45: `btn_add_acc.setStyleSheet("padding: 8px 18px;")`
- Line 51: `btn_add_txn.setStyleSheet("padding: 8px 18px;")`
- Line 145: `self.lbl_summary.setStyleSheet("font-family: Consolas, monospace; font-size: 13px; font-weight: bold;")`

### app/ui/views/dashboard_view.py (8 calls)
- Line 138: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 142: `lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 182: `lbl_quick.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 236: `lbl_d.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 261: `lbl_s.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color:#8B2635;")`
- Line 287: `lbl_chart.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 307: `lbl_r.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 332: `lbl_i.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`

### app/ui/views/daybook_view.py (2 calls)
- Line 81: `self.lbl_summary.setStyleSheet("font-size: 13px; color: #1E293B;")`
- Line 163: `btn_print.setStyleSheet("padding: 2px 6px; font-size: 11px;")`

### app/ui/views/expense_view.py (3 calls)
- Line 40: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 46: `btn_add.setStyleSheet("padding: 8px 18px; font-size: 13px;")`
- Line 111: `self.lbl_total.setStyleSheet("font-family: Consolas, monospace; font-size: 14px; font-weight: bold; color: #8B2635;")`

### app/ui/views/ledger_view.py (9 calls)
- Line 38: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 42: `lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 55: `lbl_p.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 64: `lbl_from.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 74: `lbl_to.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 118: `self.lbl_p_info.setStyleSheet("font-size: 13px; color: #1B1B18; line-height: 1.4;")`
- Line 128: `self.lbl_bal_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 133: `self.lbl_bal_headline.setStyleSheet("font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: #6B6558;")`
- Line 213: `self.lbl_bal_headline.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: {cl_color};")`

### app/ui/views/outstanding_view.py (6 calls)
- Line 201: `btn_led.setStyleSheet("padding: 2px 6px; font-size: 11px;")`
- Line 206: `btn_rem.setStyleSheet("padding: 2px 8px; font-size: 11px; font-weight: 600; color: #2F6844; border: 1px solid #2F6844; border-radius: 3px;")`
- Line 326: `lbl_party.setStyleSheet("font-size: 14px; color: #1B1B18;")`
- Line 362: `self.txt_message.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background-color: #FFFFFF; color: #1B1B18; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px;")`
- Line 370: `btn_copy.setStyleSheet("padding: 8px 16px; font-size: 12px;")`
- Line 382: `btn_send_wa.setStyleSheet("background-color: #2F6844; color: #FFFFFF; font-weight: bold; padding: 8px 20px; font-size: 13px; border-radius: 4px;")`

### app/ui/views/party_view.py (3 calls)
- Line 351: `btn_led.setStyleSheet("padding: 3px 8px; font-size: 11px;")`
- Line 356: `btn_edit.setStyleSheet("padding: 3px 8px; font-size: 11px;")`
- Line 361: `btn_del.setStyleSheet("padding: 3px 8px; font-size: 11px; color: #DC2626;")`

### app/ui/views/pnl_view.py (6 calls)
- Line 123: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 143: `btn_gen.setStyleSheet("padding: 8px 18px;")`
- Line 170: `lbl_stmt.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63; letter-spacing: 1px;")`
- Line 191: `lbl_chart.setStyleSheet("font-size: 13px; font-weight: 600; color: #2C3E63;")`
- Line 201: `self.lbl_gross_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2F6844;")`
- Line 203: `self.lbl_net_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63;")`

### app/ui/views/settings_view.py (17 calls)
- Line 109: `self.lbl_logo_path.setStyleSheet("color: #64748B; font-size: 11px;")`
- Line 128: `btn_save.setStyleSheet("padding: 8px 24px; font-size: 13px;")`
- Line 222: `lbl_info.setStyleSheet("font-size: 13px; color: #1E293B;")`
- Line 232: `btn_create_backup.setStyleSheet("padding: 10px 16px;")`
- Line 237: `btn_restore.setStyleSheet("padding: 10px 16px;")`
- Line 243: `btn_sample.setStyleSheet("padding: 10px 16px;")`
- Line 249: `btn_clear.setStyleSheet("padding: 10px 16px; background-color: #8B2635; color: white;")`
- Line 334: `stat_card.setStyleSheet(f"#Card {{ background-color: {bg_col}; border: 1px solid {border_col}; }}")`
- Line 341: `self.lbl_lic_status.setStyleSheet("font-size: 13px; color: #0F172A;")`
- Line 354: `self.lbl_m_val.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: bold; color: #0284C7;")`
- Line 356: `btn_copy_m.setStyleSheet("padding: 4px 10px; font-size: 11px;")`
- Line 375: `btn_activate.setStyleSheet("padding: 8px 24px; font-size: 13px;")`
- Line 411: `self.lbl_health_info.setStyleSheet("font-size: 13px; line-height: 1.5; color: #1E293B;")`
- Line 421: `btn_run_check.setStyleSheet("padding: 8px 16px;")`
- Line 426: `btn_thread_dump.setStyleSheet("padding: 8px 16px;")`
- Line 431: `btn_open_logs.setStyleSheet("padding: 8px 16px;")`
- Line 462: `self.txt_log_content.setStyleSheet("background-color: #1E293B; color: #F8FAFC; border-radius: 4px; padding: 6px;")`

### app/ui/views/stock_report_view.py (8 calls)
- Line 42: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 44: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 51: `btn_export.setStyleSheet("padding: 7px 14px; font-size: 12px;")`
- Line 57: `btn_refresh.setStyleSheet("padding: 7px 16px; font-size: 12px;")`
- Line 88: `lbl_range.setStyleSheet("color: #1B1B18; font-size: 12px;")`
- Line 100: `lbl_from.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 108: `lbl_to.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 132: `btn_apply.setStyleSheet("padding: 4px 12px; font-size: 12px;")`

### app/ui/views/trial_balance_view.py (5 calls)
- Line 73: `self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")`
- Line 112: `self.banner.setStyleSheet("#Card { background-color: #ECFDF5; border: 1px solid #A7F3D0; }")`
- Line 113: `self.lbl_status.setStyleSheet("font-size: 13px; color: #065F46; font-weight: bold;")`
- Line 119: `self.banner.setStyleSheet("#Card { background-color: #FEF2F2; border: 1px solid #FECACA; }")`
- Line 120: `self.lbl_status.setStyleSheet("font-size: 13px; color: #991B1B; font-weight: bold;")`

### app/ui/views/voucher_view.py (11 calls)
- Line 127: `self.lbl_party_balance.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 6px 10px; border-radius: 4px; color: #475569; font-size: 12px;")`
- Line 141: `btn_add_item.setStyleSheet("padding: 3px 10px;")`
- Line 214: `tot_panel.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 14px;")`
- Line 219: `self.lbl_taxable.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 221: `self.lbl_cgst.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 223: `self.lbl_sgst.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 225: `self.lbl_igst.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 227: `self.lbl_grand_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284C7; padding-top: 4px; border-top: 1px dashed #CBD5E1;")`
- Line 244: `self.btn_save.setStyleSheet("padding: 8px 24px; font-size: 14px;")`
- Line 250: `self.btn_save_print.setStyleSheet("padding: 8px 20px; font-size: 14px;")`
- Line 347: `btn_del.setStyleSheet("border:none; padding:2px; font-size:11px;")`

### app/ui/widgets/stat_card.py (4 calls)
- Line 15: `self.setStyleSheet(f"""`
- Line 32: `self.lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558; letter-spacing: 0.5px;")`
- Line 38: `self.lbl_value.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', 'Courier New', monospace; font-size: 24px; font-weight: bold; color: {value_color};")`
- Line 44: `self.lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`

## 3. Hardcoded Colors in UI (`#hex`, `rgb`, `QColor`, `QBrush`, `Qt.GlobalColor`)

### app/ui/theme.py (139 occurrences)
- Line 4 [#2C3E63]: `Ink Indigo (Headers, Primary Actions, Active State): #2C3E63`
- Line 5 [#A6822E]: `Ledger Brass (Accent, Column Rules, Tab Underlines): #A6822E`
- Line 6 [#8B2635]: `Ledger Maroon (Payable / Money I Owe - Red Ink):     #8B2635`
- Line 7 [#2F6844]: `Ledger Green (Receivable / Money Owed To Me):        #2F6844`
- Line 8 [#EAEAE4]: `Page Background (Cool Muted Paper-Grey):             #EAEAE4`
- Line 9 [#FBFBF9]: `Card/Panel Background (Ledger Paper White):          #FBFBF9`
- Line 10 [#D4C49E]: `Rule/Divider Lines (Brass at low opacity):           #D4C49E`
- Line 11 [#1B1B18]: `Primary Text:                                        #1B1B18`
- Line 12 [#6B6558]: `Secondary/Muted Text:                                #6B6558`
- Line 18 [#EAEAE4]: `background-color: #EAEAE4;`
- Line 19 [#1B1B18]: `color: #1B1B18;`
- Line 22 [#A6822E]: `selection-background-color: #A6822E;`
- Line 23 [#FFFFFF]: `selection-color: #FFFFFF;`
- Line 28 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 29 [#D4C49E]: `border-bottom: 1px solid #D4C49E;`
- Line 37 [#1B1B18]: `color: #1B1B18;`
- Line 42 [#6B6558]: `color: #6B6558;`
- Line 47 [#2C3E63]: `background-color: #2C3E63;`
- Line 48 [#1F2D48]: `border-right: 1px solid #1F2D48;`
- Line 53 [#FBFBF9]: `color: #FBFBF9;`
- Line 61 [#D4C49E]: `color: #D4C49E;`
- Line 71 [#DDE2EB]: `color: #DDE2EB;`
- Line 82 [#3A507D]: `background-color: #3A507D;`
- Line 83 [#FBFBF9]: `color: #FBFBF9;`
- Line 87 [#A6822E]: `background-color: #A6822E;`
- Line 88 [#FFFFFF]: `color: #FFFFFF;`
- Line 94 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 95 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 101 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 102 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 111 [#6B6558]: `color: #6B6558;`
- Line 120 [#1B1B18]: `color: #1B1B18;`
- Line 128 [#1B1B18]: `color: #1B1B18;`
- Line 135 [#1B1B18]: `color: #1B1B18;`
- Line 140 [#6B6558]: `color: #6B6558;`
- Line 145 [#FFFFFF]: `background-color: #FFFFFF;`
- Line 146 [#1B1B18]: `color: #1B1B18;`
- Line 147 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 155 [#2C3E63]: `border: 1.5px solid #2C3E63;`
- Line 156 [#FFFFFF]: `background-color: #FFFFFF;`
- Line 160 [#EAEAE4]: `background-color: #EAEAE4;`
- Line 161 [#6B6558]: `color: #6B6558;`
- Line 172 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 173 [#1B1B18]: `color: #1B1B18;`
- Line 174 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 175 [#A6822E]: `selection-background-color: #A6822E;`
- Line 176 [#FFFFFF]: `selection-color: #FFFFFF;`
- Line 182 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 183 [#2C3E63]: `color: #2C3E63;`
- Line 184 [#2C3E63]: `border: 1px solid #2C3E63;`
- Line 194 [#EAEAE4]: `background-color: #EAEAE4;`
- Line 198 [#D4C49E]: `background-color: #D4C49E;`
- Line 202 [#2C3E63]: `background-color: #2C3E63;`
- Line 203 [#FBFBF9]: `color: #FBFBF9;`
- Line 211 [#3A507D]: `background-color: #3A507D;`
- Line 215 [#1F2D48]: `background-color: #1F2D48;`
- Line 219 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 220 [#2C3E63]: `color: #2C3E63;`
- Line 221 [#2C3E63]: `border: 1px solid #2C3E63;`
- Line 227 [#EAEAE4]: `background-color: #EAEAE4;`
- Line 231 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 232 [#8B2635]: `color: #8B2635;`
- Line 233 [#8B2635]: `border: 1px solid #8B2635;`
- Line 239 [#8B2635]: `background-color: #8B2635;`
- Line 240 [#FBFBF9]: `color: #FBFBF9;`
- Line 244 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 245 [#2F6844]: `color: #2F6844;`
- Line 246 [#2F6844]: `border: 1px solid #2F6844;`
- Line 252 [#2F6844]: `background-color: #2F6844;`
- Line 253 [#FBFBF9]: `color: #FBFBF9;`
- Line 257 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 258 [#2C3E63]: `color: #2C3E63;`
- Line 259 [#2C3E63]: `border: 1px solid #2C3E63;`
- Line 265 [#EAEAE4]: `background-color: #EAEAE4;`
- Line 269 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 270 [#8B2635]: `color: #8B2635;`
- Line 271 [#8B2635]: `border: 1px solid #8B2635;`
- Line 277 [#8B2635]: `background-color: #8B2635;`
- Line 278 [#FBFBF9]: `color: #FBFBF9;`
- Line 285 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 286 [#FBFBF9]: `alternate-background-color: #FBFBF9; /* Pure continuous ledger paper, no zebra striping */`
- Line 287 [#D4C49E]: `gridline-color: #D4C49E;            /* Brass ruled vertical/horizontal lines (1px) */`
- Line 288 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 290 [#A6822E]: `selection-background-color: #A6822E;`
- Line 291 [#FFFFFF]: `selection-color: #FFFFFF;`
- Line 293 [#1B1B18]: `color: #1B1B18;`
- Line 297 [#F1F1EB]: `background-color: #F1F1EB;`
- Line 298 [#1B1B18]: `color: #1B1B18;`
- Line 301 [#D4C49E]: `border-right: 1px solid #D4C49E;     /* Ruled vertical column separator */`
- Line 302 [#A6822E]: `border-bottom: 3px double #A6822E;   /* Signature double horizontal ledger rule */`
- Line 311 [#EAEAE4]: `background-color: #EAEAE4;`
- Line 316 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 318 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 323 [#EAEAE4]: `background-color: #EAEAE4;`
- Line 324 [#6B6558]: `color: #6B6558;`
- Line 325 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 335 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 336 [#2C3E63]: `color: #2C3E63;`
- Line 337 [#A6822E]: `border-bottom: 2px solid #A6822E; /* Ledger Brass active tab underline */`
- Line 341 [#D4C49E]: `background-color: #D4C49E;`
- Line 346 [#EAEAE4]: `background: #EAEAE4;`
- Line 352 [#D4C49E]: `background: #D4C49E;`
- Line 358 [#A6822E]: `background: #A6822E;`
- Line 366 [#EAEAE4]: `background: #EAEAE4;`
- Line 372 [#D4C49E]: `background: #D4C49E;`
- Line 378 [#A6822E]: `background: #A6822E;`
- Line 387 [#2C3E63]: `background-color: #2C3E63;`
- Line 388 [#FBFBF9]: `color: #FBFBF9;`
- Line 389 [#A6822E]: `border-top: 1px solid #A6822E;`
- Line 395 [#FBFBF9]: `color: #FBFBF9;`
- Line 402 [#6B6558]: `return "<span style='font-family: Consolas, Cascadia Mono, monospace; color: #6B6558; font-weight: bold;'>₹0.00 Nil</span>"`
- Line 404 [#2F6844]: `# Receivable - Money owed TO me: #2F6844 (Ledger Green)`
- Line 405 [#2F6844]: `return f"<span style='font-family: Consolas, Cascadia Mono, monospace; color: #2F6844; font-weight: bold;'>₹{amount:,.2f} Dr</span>"`
- Line 407 [#8B2635]: `# Payable - Money I owe: #8B2635 (Ledger Maroon / Red-ink debit)`
- Line 408 [#8B2635]: `return f"<span style='font-family: Consolas, Cascadia Mono, monospace; color: #8B2635; font-weight: bold;'>₹{amount:,.2f} Cr</span>"`
- Line 413 [#E8ECF2]: `"Debit": ("#E8ECF2", "#2C3E63", "#C4CEDD"),`
- Line 413 [#2C3E63]: `"Debit": ("#E8ECF2", "#2C3E63", "#C4CEDD"),`
- Line 413 [#C4CEDD]: `"Debit": ("#E8ECF2", "#2C3E63", "#C4CEDD"),`
- Line 414 [#E9F2EC]: `"Credit": ("#E9F2EC", "#2F6844", "#B8D8C2"),`
- Line 414 [#2F6844]: `"Credit": ("#E9F2EC", "#2F6844", "#B8D8C2"),`
- Line 414 [#B8D8C2]: `"Credit": ("#E9F2EC", "#2F6844", "#B8D8C2"),`
- Line 415 [#F5EDE8]: `"Journal": ("#F5EDE8", "#8B2635", "#DEC5BB"),`
- Line 415 [#8B2635]: `"Journal": ("#F5EDE8", "#8B2635", "#DEC5BB"),`
- Line 415 [#DEC5BB]: `"Journal": ("#F5EDE8", "#8B2635", "#DEC5BB"),`
- Line 416 [#E8ECF2]: `"Sale": ("#E8ECF2", "#2C3E63", "#C4CEDD"),`
- Line 416 [#2C3E63]: `"Sale": ("#E8ECF2", "#2C3E63", "#C4CEDD"),`
- Line 416 [#C4CEDD]: `"Sale": ("#E8ECF2", "#2C3E63", "#C4CEDD"),`
- Line 417 [#E9F2EC]: `"Purchase": ("#E9F2EC", "#2F6844", "#B8D8C2"),`
- Line 417 [#2F6844]: `"Purchase": ("#E9F2EC", "#2F6844", "#B8D8C2"),`
- Line 417 [#B8D8C2]: `"Purchase": ("#E9F2EC", "#2F6844", "#B8D8C2"),`
- Line 418 [#E8ECF2]: `"Payment": ("#E8ECF2", "#2C3E63", "#C4CEDD"),`
- Line 418 [#2C3E63]: `"Payment": ("#E8ECF2", "#2C3E63", "#C4CEDD"),`
- Line 418 [#C4CEDD]: `"Payment": ("#E8ECF2", "#2C3E63", "#C4CEDD"),`
- Line 419 [#E9F2EC]: `"Receipt": ("#E9F2EC", "#2F6844", "#B8D8C2")`
- Line 419 [#2F6844]: `"Receipt": ("#E9F2EC", "#2F6844", "#B8D8C2")`
- Line 419 [#B8D8C2]: `"Receipt": ("#E9F2EC", "#2F6844", "#B8D8C2")`
- Line 421 [#F1F1EB]: `bg, fg, border = colors_map.get(v_type, ("#F1F1EB", "#1B1B18", "#D4C49E"))`
- Line 421 [#1B1B18]: `bg, fg, border = colors_map.get(v_type, ("#F1F1EB", "#1B1B18", "#D4C49E"))`
- Line 421 [#D4C49E]: `bg, fg, border = colors_map.get(v_type, ("#F1F1EB", "#1B1B18", "#D4C49E"))`

### app/ui/views/dashboard_view.py (43 occurrences)
- Line 59 [#D4C49E]: `# Draw Y-axis gridlines and labels (#D4C49E brass ruled line, #6B6558 muted text)`
- Line 59 [#6B6558]: `# Draw Y-axis gridlines and labels (#D4C49E brass ruled line, #6B6558 muted text)`
- Line 60 [#D4C49E]: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 60 [QColor("#D4C49E")]: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 66 [#6B6558]: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 66 [QColor("#6B6558")]: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 75 [#D4C49E]: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 75 [QColor("#D4C49E")]: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 81 [#2C3E63]: `# Debits bar: Solid #2C3E63 (Ink Indigo)`
- Line 85 [#2C3E63]: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 85 [QColor("#2C3E63")]: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 85 [QBrush(QColor("#2C3E63")]: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 89 [#A6822E]: `# Credits bar: Solid #A6822E (Ledger Brass)`
- Line 93 [#A6822E]: `painter.setBrush(QBrush(QColor("#A6822E")))`
- Line 93 [QColor("#A6822E")]: `painter.setBrush(QBrush(QColor("#A6822E")))`
- Line 93 [QBrush(QColor("#A6822E")]: `painter.setBrush(QBrush(QColor("#A6822E")))`
- Line 97 [#6B6558]: `# Month label (12px, #6B6558)`
- Line 98 [#6B6558]: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 98 [QColor("#6B6558")]: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 106 [#2C3E63]: `painter.setBrush(QColor("#2C3E63"))`
- Line 106 [QColor("#2C3E63")]: `painter.setBrush(QColor("#2C3E63"))`
- Line 108 [#1B1B18]: `painter.setPen(QColor("#1B1B18"))`
- Line 108 [QColor("#1B1B18")]: `painter.setPen(QColor("#1B1B18"))`
- Line 113 [#A6822E]: `painter.setBrush(QColor("#A6822E"))`
- Line 113 [QColor("#A6822E")]: `painter.setBrush(QColor("#A6822E"))`
- Line 115 [#1B1B18]: `painter.setPen(QColor("#1B1B18"))`
- Line 115 [QColor("#1B1B18")]: `painter.setPen(QColor("#1B1B18"))`
- Line 138 [#1B1B18]: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 142 [#6B6558]: `lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 151 [#2F6844]: `self.card_inv_amt = StatCard("Today's Sales (Invoices)", "₹0.00", "Total sales today", value_color="#2F6844")`
- Line 152 [#1B1B18]: `self.card_inv_cnt = StatCard("Invoices Today", "0", "Count of invoices", value_color="#1B1B18")`
- Line 153 [#A6822E]: `self.card_prof = StatCard("Pending Quotations", "0", "Sent proformas", value_color="#A6822E")`
- Line 154 [#8B2635]: `self.card_stock = StatCard("Low Stock Alerts", "0", "Items needing reorder", value_color="#8B2635")`
- Line 164 [#2F6844]: `self.card_rec = StatCard("Total Receivables (Debtors)", "₹0.00", "Money owed to you", value_color="#2F6844")`
- Line 165 [#8B2635]: `self.card_pay = StatCard("Total Payables (Creditors)", "₹0.00", "Money you owe", value_color="#8B2635")`
- Line 166 [#2C3E63]: `self.card_sales = StatCard("Today's Debits", "₹0.00", "Billed today", value_color="#2C3E63")`
- Line 167 [#1B1B18]: `self.card_rec_today = StatCard("Today's Collections", "₹0.00", "Collected today", value_color="#1B1B18")`
- Line 182 [#1B1B18]: `lbl_quick.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 261 [#8B2635]: `lbl_s.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color:#8B2635;")`
- Line 382 [#2F6844]: `it_amt.setForeground(QColor("#2F6844"))`
- Line 382 [QColor("#2F6844")]: `it_amt.setForeground(QColor("#2F6844"))`
- Line 395 [#8B2635]: `it_stock.setForeground(QColor("#8B2635"))`
- Line 395 [QColor("#8B2635")]: `it_stock.setForeground(QColor("#8B2635"))`

### app/ui/views/pnl_view.py (39 occurrences)
- Line 55 [#D4C49E]: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 55 [QColor("#D4C49E")]: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 60 [#6B6558]: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 60 [QColor("#6B6558")]: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 69 [#D4C49E]: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 69 [QColor("#D4C49E")]: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 75 [#2C3E63]: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 75 [QColor("#2C3E63")]: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 75 [QBrush(QColor("#2C3E63")]: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 82 [#2F6844]: `color = QColor("#2F6844") if np_val >= 0 else QColor("#8B2635")`
- Line 82 [#8B2635]: `color = QColor("#2F6844") if np_val >= 0 else QColor("#8B2635")`
- Line 82 [QColor("#2F6844")]: `color = QColor("#2F6844") if np_val >= 0 else QColor("#8B2635")`
- Line 82 [QColor("#8B2635")]: `color = QColor("#2F6844") if np_val >= 0 else QColor("#8B2635")`
- Line 83 [QBrush(color)]: `painter.setBrush(QBrush(color))`
- Line 87 [#6B6558]: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 87 [QColor("#6B6558")]: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 93 [#2C3E63]: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 93 [QColor("#2C3E63")]: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 93 [QBrush(QColor("#2C3E63")]: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 96 [#1B1B18]: `painter.setPen(QPen(QColor("#1B1B18"), 1))`
- Line 96 [QColor("#1B1B18")]: `painter.setPen(QPen(QColor("#1B1B18"), 1))`
- Line 99 [#2F6844]: `painter.setBrush(QBrush(QColor("#2F6844")))`
- Line 99 [QColor("#2F6844")]: `painter.setBrush(QBrush(QColor("#2F6844")))`
- Line 99 [QBrush(QColor("#2F6844")]: `painter.setBrush(QBrush(QColor("#2F6844")))`
- Line 102 [#1B1B18]: `painter.setPen(QPen(QColor("#1B1B18"), 1))`
- Line 102 [QColor("#1B1B18")]: `painter.setPen(QPen(QColor("#1B1B18"), 1))`
- Line 123 [#1B1B18]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 170 [#2C3E63]: `lbl_stmt.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63; letter-spacing: 1px;")`
- Line 191 [#2C3E63]: `lbl_chart.setStyleSheet("font-size: 13px; font-weight: 600; color: #2C3E63;")`
- Line 201 [#2F6844]: `self.lbl_gross_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2F6844;")`
- Line 203 [#2C3E63]: `self.lbl_net_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63;")`
- Line 229 [#2F6844]: `net_color = "#2F6844" if net >= 0 else "#8B2635"`
- Line 229 [#8B2635]: `net_color = "#2F6844" if net >= 0 else "#8B2635"`
- Line 263 [#2C3E63]: `lbl_item.setForeground(QColor("#2C3E63"))`
- Line 263 [QColor("#2C3E63")]: `lbl_item.setForeground(QColor("#2C3E63"))`
- Line 274 [#2F6844]: `amt_item.setForeground(QColor("#2F6844"))`
- Line 274 [QColor("#2F6844")]: `amt_item.setForeground(QColor("#2F6844"))`
- Line 276 [#8B2635]: `amt_item.setForeground(QColor("#8B2635"))`
- Line 276 [QColor("#8B2635")]: `amt_item.setForeground(QColor("#8B2635"))`

### app/ui/views/billing/quotation_view.py (37 occurrences)
- Line 36 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 37 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 94 [#1B1B18]: `self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px; color: #1B1B18;")`
- Line 101 [#8B2635]: `btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px; background: transparent;")`
- Line 101 [#8B2635]: `btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px; background: transparent;")`
- Line 187 [#1B1B18]: `lbl_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 193 [#D4C49E]: `QTabWidget::pane { border: 1px solid #D4C49E; background: #FFFFFF; border-radius: 4px; }`
- Line 193 [#FFFFFF]: `QTabWidget::pane { border: 1px solid #D4C49E; background: #FFFFFF; border-radius: 4px; }`
- Line 194 [#EFECE6]: `QTabBar::tab { background: #EFECE6; color: #6B6558; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }`
- Line 194 [#6B6558]: `QTabBar::tab { background: #EFECE6; color: #6B6558; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }`
- Line 195 [#FFFFFF]: `QTabBar::tab:selected { background: #FFFFFF; color: #1B1B18; font-weight: 600; border: 1px solid #D4C49E; border-bottom: none; }`
- Line 195 [#1B1B18]: `QTabBar::tab:selected { background: #FFFFFF; color: #1B1B18; font-weight: 600; border: 1px solid #D4C49E; border-bottom: none; }`
- Line 195 [#D4C49E]: `QTabBar::tab:selected { background: #FFFFFF; color: #1B1B18; font-weight: 600; border: 1px solid #D4C49E; border-bottom: none; }`
- Line 309 [#D4C49E]: `scroll.setStyleSheet("QScrollArea { border: 1px solid #D4C49E; background: #FFFFFF; border-radius: 4px; }")`
- Line 309 [#FFFFFF]: `scroll.setStyleSheet("QScrollArea { border: 1px solid #D4C49E; background: #FFFFFF; border-radius: 4px; }")`
- Line 400 [#F7F5EE]: `summary_frame.setStyleSheet("background-color: #F7F5EE; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px 16px;")`
- Line 400 [#D4C49E]: `summary_frame.setStyleSheet("background-color: #F7F5EE; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px 16px;")`
- Line 405 [#1B1B18]: `self.lbl_subtotal.setStyleSheet("font-family: Consolas; font-weight: 600; color: #1B1B18;")`
- Line 410 [#2C3E63]: `self.lbl_tax.setStyleSheet("font-family: Consolas; font-weight: 600; color: #2C3E63;")`
- Line 415 [#2F6844]: `self.lbl_grand_total.setStyleSheet("font-family: Consolas; font-size: 15px; font-weight: bold; color: #2F6844;")`
- Line 606 [#1B1B18]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 609 [#6B6558]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 630 [#1B1B18]: `self.card_total = StatCard("TOTAL QUOTATIONS", "0", "Total Value: ₹0.00", value_color="#1B1B18")`
- Line 631 [#A6822E]: `self.card_draft = StatCard("DRAFT / IN-PROGRESS", "0", "Pending review", value_color="#A6822E")`
- Line 632 [#2C3E63]: `self.card_sent = StatCard("SENT TO CLIENTS", "0", "Awaiting response", value_color="#2C3E63")`
- Line 633 [#2F6844]: `self.card_won = StatCard("ACCEPTED / CONVERTED", "0", "Won proposals", value_color="#2F6844")`
- Line 646 [#FFFFFF]: `background-color: #FFFFFF;`
- Line 647 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 693 [#6B6558]: `self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 785 [#A6822E]: `"draft": "#A6822E",`
- Line 786 [#2C3E63]: `"sent": "#2C3E63",`
- Line 787 [#2F6844]: `"accepted": "#2F6844",`
- Line 788 [#155724]: `"converted": "#155724",`
- Line 789 [#8B2635]: `"rejected": "#8B2635",`
- Line 790 [#6B6558]: `"expired": "#6B6558"`
- Line 792 [#1B1B18]: `it_s.setForeground(QColor(color_map.get(stat, "#1B1B18")))`
- Line 792 [QColor(color_map.get(stat, "#1B1B18")]: `it_s.setForeground(QColor(color_map.get(stat, "#1B1B18")))`

### app/ui/views/outstanding_view.py (22 occurrences)
- Line 43 [#0284C7]: `accent = "#0284C7" if self.report_type == "Receivables" else "#D97706"`
- Line 43 [#D97706]: `accent = "#0284C7" if self.report_type == "Receivables" else "#D97706"`
- Line 45 [#10B981]: `self.card_0_30 = StatCard("0 - 30 Days", "₹0.00", "Current period", "#10B981")`
- Line 46 [#0284C7]: `self.card_31_60 = StatCard("31 - 60 Days", "₹0.00", "Moderate age", "#0284C7")`
- Line 47 [#F59E0B]: `self.card_61_90 = StatCard("61 - 90 Days", "₹0.00", "Follow-up required", "#F59E0B")`
- Line 48 [#EF4444]: `self.card_90_plus = StatCard("90+ Days", "₹0.00", "Critical overdue", "#EF4444")`
- Line 170 [#D97706]: `it_61_90.setForeground(QColor("#D97706"))`
- Line 170 [QColor("#D97706")]: `it_61_90.setForeground(QColor("#D97706"))`
- Line 175 [#DC2626]: `it_90.setForeground(QColor("#DC2626"))`
- Line 175 [QColor("#DC2626")]: `it_90.setForeground(QColor("#DC2626"))`
- Line 181 [#0284C7]: `accent_col = "#0284C7" if self.report_type == "Receivables" else "#D97706"`
- Line 181 [#D97706]: `accent_col = "#0284C7" if self.report_type == "Receivables" else "#D97706"`
- Line 182 [QColor(accent_col)]: `it_tot.setForeground(QColor(accent_col))`
- Line 206 [#2F6844]: `btn_rem.setStyleSheet("padding: 2px 8px; font-size: 11px; font-weight: 600; color: #2F6844; border: 1px solid #2F6844; border-radius: 3px;")`
- Line 206 [#2F6844]: `btn_rem.setStyleSheet("padding: 2px 8px; font-size: 11px; font-weight: 600; color: #2F6844; border: 1px solid #2F6844; border-radius: 3px;")`
- Line 326 [#1B1B18]: `lbl_party.setStyleSheet("font-size: 14px; color: #1B1B18;")`
- Line 330 [#8B2635]: `lbl_due = QLabel(f"<b>Total Outstanding Balance:</b> <span style='color: #8B2635; font-size: 15px; font-weight: bold;'>₹{tot:,.2f}</span>")`
- Line 362 [#FFFFFF]: `self.txt_message.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background-color: #FFFFFF; color: #1B1B18; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px;")`
- Line 362 [#1B1B18]: `self.txt_message.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background-color: #FFFFFF; color: #1B1B18; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px;")`
- Line 362 [#D4C49E]: `self.txt_message.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background-color: #FFFFFF; color: #1B1B18; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px;")`
- Line 382 [#2F6844]: `btn_send_wa.setStyleSheet("background-color: #2F6844; color: #FFFFFF; font-weight: bold; padding: 8px 20px; font-size: 13px; border-radius: 4px;")`
- Line 382 [#FFFFFF]: `btn_send_wa.setStyleSheet("background-color: #2F6844; color: #FFFFFF; font-weight: bold; padding: 8px 20px; font-size: 13px; border-radius: 4px;")`

### app/ui/views/stock_report_view.py (20 occurrences)
- Line 42 [#1B1B18]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 44 [#6B6558]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 66 [#2C3E63]: `self.card_sales = StatCard("Total Sales Revenue", f"{CURRENCY_SYMBOL}0.00", "Billed sales in period", "#2C3E63")`
- Line 67 [#A6822E]: `self.card_purchases = StatCard("Total Purchase Cost", f"{CURRENCY_SYMBOL}0.00", "Purchased goods cost", "#A6822E")`
- Line 68 [#2F6844]: `self.card_profit = StatCard("Gross Profit", f"{CURRENCY_SYMBOL}0.00", "Sales minus COGS", "#2F6844")`
- Line 69 [#0284C7]: `self.card_stock_val = StatCard("Total Stock Value", f"{CURRENCY_SYMBOL}0.00", "Closing inventory valuation", "#0284C7")`
- Line 70 [#8B2635]: `self.card_low_stock = StatCard("Low Stock Items", "0", "Require re-order", "#8B2635")`
- Line 88 [#1B1B18]: `lbl_range.setStyleSheet("color: #1B1B18; font-size: 12px;")`
- Line 100 [#6B6558]: `lbl_from.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 108 [#6B6558]: `lbl_to.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 289 [#8B2635]: `it_stock.setForeground(QColor("#8B2635"))`
- Line 289 [QColor("#8B2635")]: `it_stock.setForeground(QColor("#8B2635"))`
- Line 315 [#2F6844]: `it_profit.setForeground(QColor("#2F6844"))`
- Line 315 [QColor("#2F6844")]: `it_profit.setForeground(QColor("#2F6844"))`
- Line 317 [#8B2635]: `it_profit.setForeground(QColor("#8B2635"))`
- Line 317 [QColor("#8B2635")]: `it_profit.setForeground(QColor("#8B2635"))`
- Line 324 [#2F6844]: `it_margin.setForeground(QColor("#2F6844"))`
- Line 324 [QColor("#2F6844")]: `it_margin.setForeground(QColor("#2F6844"))`
- Line 326 [#8B2635]: `it_margin.setForeground(QColor("#8B2635"))`
- Line 326 [QColor("#8B2635")]: `it_margin.setForeground(QColor("#8B2635"))`

### app/ui/views/ledger_view.py (17 occurrences)
- Line 38 [#1B1B18]: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 42 [#6B6558]: `lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 55 [#6B6558]: `lbl_p.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 64 [#6B6558]: `lbl_from.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 74 [#6B6558]: `lbl_to.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 118 [#1B1B18]: `self.lbl_p_info.setStyleSheet("font-size: 13px; color: #1B1B18; line-height: 1.4;")`
- Line 128 [#6B6558]: `self.lbl_bal_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 133 [#6B6558]: `self.lbl_bal_headline.setStyleSheet("font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: #6B6558;")`
- Line 191 [#1B1B18]: `f"<span style='font-family: \"Bahnschrift\", \"Segoe UI Semibold\", sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;'>{p['name']}</span> "`
- Line 192 [#6B6558]: `f"<span style='font-size: 12px; color: #6B6558;'>({location or 'Local'})</span><br/>"`
- Line 193 [#6B6558]: `f"<span style='font-size: 12px; color: #6B6558;'>GSTIN: {gst_str} | Phone: {phone_str} | Credit Period: {p.get('credit_period_days', 30)} Days</span>"`
- Line 201 [#2F6844]: `# Headline Closing Balance: Money owed TO me (Dr) in #2F6844 (Ledger Green), Money I owe (Cr) in #8B2635 (Ledger Maroon)`
- Line 201 [#8B2635]: `# Headline Closing Balance: Money owed TO me (Dr) in #2F6844 (Ledger Green), Money I owe (Cr) in #8B2635 (Ledger Maroon)`
- Line 203 [#6B6558]: `cl_color = "#6B6558"`
- Line 205 [#2F6844]: `cl_color = "#2F6844"  # Receivable`
- Line 207 [#8B2635]: `cl_color = "#8B2635"  # Payable`
- Line 315 [QColor(cl_color)]: `it_t_cl.setForeground(QColor(cl_color))`

### app/ui/views/billing/invoice_view.py (16 occurrences)
- Line 30 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 31 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 90 [#8B2635]: `btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px;")`
- Line 90 [#8B2635]: `btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px;")`
- Line 193 [#1B1B18]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 290 [#1B1B18]: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 304 [#6B6558]: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 338 [#2C3E63]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63;")`
- Line 556 [#1B1B18]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 559 [#6B6558]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 617 [#6B6558]: `self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 670 [#A6822E]: `color_map = {"draft": "#A6822E", "final": "#2F6844", "cancelled": "#8B2635"}`
- Line 670 [#2F6844]: `color_map = {"draft": "#A6822E", "final": "#2F6844", "cancelled": "#8B2635"}`
- Line 670 [#8B2635]: `color_map = {"draft": "#A6822E", "final": "#2F6844", "cancelled": "#8B2635"}`
- Line 671 [#1B1B18]: `it_st.setForeground(QColor(color_map.get(status, "#1B1B18")))`
- Line 671 [QColor(color_map.get(status, "#1B1B18")]: `it_st.setForeground(QColor(color_map.get(status, "#1B1B18")))`

### app/ui/views/settings_view.py (14 occurrences)
- Line 109 [#64748B]: `self.lbl_logo_path.setStyleSheet("color: #64748B; font-size: 11px;")`
- Line 222 [#1E293B]: `lbl_info.setStyleSheet("font-size: 13px; color: #1E293B;")`
- Line 249 [#8B2635]: `btn_clear.setStyleSheet("padding: 10px 16px; background-color: #8B2635; color: white;")`
- Line 332 [#ECFDF5]: `bg_col = "#ECFDF5" if lic["is_licensed"] else "#FFFBEB"`
- Line 332 [#FFFBEB]: `bg_col = "#ECFDF5" if lic["is_licensed"] else "#FFFBEB"`
- Line 333 [#A7F3D0]: `border_col = "#A7F3D0" if lic["is_licensed"] else "#FDE68A"`
- Line 333 [#FDE68A]: `border_col = "#A7F3D0" if lic["is_licensed"] else "#FDE68A"`
- Line 341 [#0F172A]: `self.lbl_lic_status.setStyleSheet("font-size: 13px; color: #0F172A;")`
- Line 354 [#0284C7]: `self.lbl_m_val.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: bold; color: #0284C7;")`
- Line 411 [#1E293B]: `self.lbl_health_info.setStyleSheet("font-size: 13px; line-height: 1.5; color: #1E293B;")`
- Line 462 [#1E293B]: `self.txt_log_content.setStyleSheet("background-color: #1E293B; color: #F8FAFC; border-radius: 4px; padding: 6px;")`
- Line 462 [#F8FAFC]: `self.txt_log_content.setStyleSheet("background-color: #1E293B; color: #F8FAFC; border-radius: 4px; padding: 6px;")`
- Line 473 [#2F6844]: `status_col = "#2F6844" if report["status"] == "HEALTHY" else "#8B2635"`
- Line 473 [#8B2635]: `status_col = "#2F6844" if report["status"] == "HEALTHY" else "#8B2635"`

### app/ui/views/cashbank_view.py (13 occurrences)
- Line 39 [#1B1B18]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 181 [#2F6844]: `bal_item.setForeground(QColor("#2F6844"))`
- Line 181 [QColor("#2F6844")]: `bal_item.setForeground(QColor("#2F6844"))`
- Line 183 [#8B2635]: `bal_item.setForeground(QColor("#8B2635"))`
- Line 183 [QColor("#8B2635")]: `bal_item.setForeground(QColor("#8B2635"))`
- Line 229 [#2F6844]: `r_item.setForeground(QColor("#2F6844"))`
- Line 229 [QColor("#2F6844")]: `r_item.setForeground(QColor("#2F6844"))`
- Line 234 [#8B2635]: `p_item.setForeground(QColor("#8B2635"))`
- Line 234 [QColor("#8B2635")]: `p_item.setForeground(QColor("#8B2635"))`
- Line 267 [#2F6844]: `r_item.setForeground(QColor("#2F6844"))`
- Line 267 [QColor("#2F6844")]: `r_item.setForeground(QColor("#2F6844"))`
- Line 272 [#8B2635]: `p_item.setForeground(QColor("#8B2635"))`
- Line 272 [QColor("#8B2635")]: `p_item.setForeground(QColor("#8B2635"))`

### app/ui/views/voucher_view.py (13 occurrences)
- Line 102 [#8891]: `self.inp_ref.setPlaceholderText("e.g. Inv #8891 / UTR No")`
- Line 127 [#F8FAFC]: `self.lbl_party_balance.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 6px 10px; border-radius: 4px; color: #475569; font-size: 12px;")`
- Line 127 [#E2E8F0]: `self.lbl_party_balance.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 6px 10px; border-radius: 4px; color: #475569; font-size: 12px;")`
- Line 127 [#475569]: `self.lbl_party_balance.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 6px 10px; border-radius: 4px; color: #475569; font-size: 12px;")`
- Line 214 [#F8FAFC]: `tot_panel.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 14px;")`
- Line 214 [#CBD5E1]: `tot_panel.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 14px;")`
- Line 219 [#475569]: `self.lbl_taxable.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 221 [#475569]: `self.lbl_cgst.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 223 [#475569]: `self.lbl_sgst.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 225 [#475569]: `self.lbl_igst.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 227 [#0284C7]: `self.lbl_grand_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284C7; padding-top: 4px; border-top: 1px dashed #CBD5E1;")`
- Line 227 [#CBD5E1]: `self.lbl_grand_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284C7; padding-top: 4px; border-top: 1px dashed #CBD5E1;")`
- Line 296 [#0284C7]: `f"<b>Party Selected:</b> {p['name']} | <b>GSTIN:</b> {gst_str} | <b>State:</b> {p.get('state','Maharashtra')} ({p.get('state_code','27')}) | <b>Current Balance:</b> <font color='#0284C7'><b>{bal_str}</b></font>"`

### app/ui/views/billing/proforma_view.py (13 occurrences)
- Line 62 [#1B1B18]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 159 [#1B1B18]: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 173 [#6B6558]: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 206 [#2C3E63]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63;")`
- Line 424 [#1B1B18]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 427 [#6B6558]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 474 [#6B6558]: `self.lbl_count.setStyleSheet("color: #6B6558;")`
- Line 531 [#A6822E]: `color_map = {"draft": "#A6822E", "sent": "#2C3E63", "converted": "#2F6844", "expired": "#8B2635"}`
- Line 531 [#2C3E63]: `color_map = {"draft": "#A6822E", "sent": "#2C3E63", "converted": "#2F6844", "expired": "#8B2635"}`
- Line 531 [#2F6844]: `color_map = {"draft": "#A6822E", "sent": "#2C3E63", "converted": "#2F6844", "expired": "#8B2635"}`
- Line 531 [#8B2635]: `color_map = {"draft": "#A6822E", "sent": "#2C3E63", "converted": "#2F6844", "expired": "#8B2635"}`
- Line 532 [#1B1B18]: `it_s.setForeground(QColor(color_map.get(status, "#1B1B18")))`
- Line 532 [QColor(color_map.get(status, "#1B1B18")]: `it_s.setForeground(QColor(color_map.get(status, "#1B1B18")))`

### app/ui/views/billing/product_view.py (12 occurrences)
- Line 47 [#1B1B18]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 168 [#1B1B18]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 171 [#6B6558]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 254 [#6B6558]: `self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 302 [#8B2635]: `it_stock.setForeground(QColor("#8B2635"))`
- Line 302 [QColor("#8B2635")]: `it_stock.setForeground(QColor("#8B2635"))`
- Line 304 [#2F6844]: `it_stock.setForeground(QColor("#2F6844"))`
- Line 304 [QColor("#2F6844")]: `it_stock.setForeground(QColor("#2F6844"))`
- Line 310 [#8B2635]: `it_status.setForeground(QColor("#8B2635"))`
- Line 310 [QColor("#8B2635")]: `it_status.setForeground(QColor("#8B2635"))`
- Line 312 [#2F6844]: `it_status.setForeground(QColor("#2F6844"))`
- Line 312 [QColor("#2F6844")]: `it_status.setForeground(QColor("#2F6844"))`

### app/ui/views/billing/billing_reports_view.py (11 occurrences)
- Line 31 [#1B1B18]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 34 [#6B6558]: `ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 42 [#2C3E63]: `self.card_today = self._card("Today's Sales", "₹0", "#2C3E63")`
- Line 43 [#2F6844]: `self.card_month = self._card("Monthly Revenue", "₹0", "#2F6844")`
- Line 44 [#8B2635]: `self.card_stock = self._card("Low Stock Items", "0", "#8B2635")`
- Line 45 [#A6822E]: `self.card_returns = self._card("Pending Returns", "0", "#A6822E")`
- Line 52 [#2C3E63]: `self.card_invoices = self._card("Total Invoices", "0", "#2C3E63")`
- Line 53 [#7D5A8F]: `self.card_proformas = self._card("Proformas", "0", "#7D5A8F")`
- Line 54 [#A6822E]: `self.card_pos = self._card("Purchase Orders", "0", "#A6822E")`
- Line 55 [#3F7A56]: `self.card_challans = self._card("Delivery Challans", "0", "#3F7A56")`
- Line 79 [#6B6558]: `lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`

### app/ui/views/billing/purchase_order_view.py (11 occurrences)
- Line 33 [#1B1B18]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;"); layout.addWidget(title)`
- Line 63 [#2C3E63]: `self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas;")`
- Line 122 [#1B1B18]: `lbl = QLabel("Purchase Orders"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 124 [#6B6558]: `ls = QLabel("Create and track purchase orders to suppliers"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 147 [#6B6558]: `self.lbl_count = QLabel("0 orders"); self.lbl_count.setStyleSheet("color: #6B6558;")`
- Line 171 [#A6822E]: `cm = {"draft": "#A6822E", "sent": "#2C3E63", "received": "#2F6844", "cancelled": "#8B2635"}`
- Line 171 [#2C3E63]: `cm = {"draft": "#A6822E", "sent": "#2C3E63", "received": "#2F6844", "cancelled": "#8B2635"}`
- Line 171 [#2F6844]: `cm = {"draft": "#A6822E", "sent": "#2C3E63", "received": "#2F6844", "cancelled": "#8B2635"}`
- Line 171 [#8B2635]: `cm = {"draft": "#A6822E", "sent": "#2C3E63", "received": "#2F6844", "cancelled": "#8B2635"}`
- Line 172 [#1B1B18]: `it_s.setForeground(QColor(cm.get(st, "#1B1B18"))); self.table.setItem(row, 5, it_s)`
- Line 172 [QColor(cm.get(st, "#1B1B18")]: `it_s.setForeground(QColor(cm.get(st, "#1B1B18"))); self.table.setItem(row, 5, it_s)`

### app/ui/main_window.py (9 occurrences)
- Line 87 [#A69876]: `section_bill.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 8px 8px 4px 8px;")`
- Line 116 [#A69876]: `section_acct.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")`
- Line 145 [#A69876]: `section_sys.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")`
- Line 161 [#D4C49E]: `self.lbl_lic_badge.setStyleSheet("color: #D4C49E; font-size: 11px; font-weight: 600; padding: 6px;")`
- Line 193 [#475569]: `self.lbl_clock.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569; background-color: #F1F5F9; padding: 4px 10px; border-radius: 4px;")`
- Line 193 [#F1F5F9]: `self.lbl_clock.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569; background-color: #F1F5F9; padding: 4px 10px; border-radius: 4px;")`
- Line 418 [#2F6844]: `warn_text = "<span style='color:#2F6844;'>None (System running optimally)</span>"`
- Line 421 [#2F6844]: `status_color = "#2F6844" if report["status"] == "HEALTHY" else "#8B2635"`
- Line 421 [#8B2635]: `status_color = "#2F6844" if report["status"] == "HEALTHY" else "#8B2635"`

### app/ui/views/trial_balance_view.py (8 occurrences)
- Line 112 [#ECFDF5]: `self.banner.setStyleSheet("#Card { background-color: #ECFDF5; border: 1px solid #A7F3D0; }")`
- Line 112 [#A7F3D0]: `self.banner.setStyleSheet("#Card { background-color: #ECFDF5; border: 1px solid #A7F3D0; }")`
- Line 113 [#065F46]: `self.lbl_status.setStyleSheet("font-size: 13px; color: #065F46; font-weight: bold;")`
- Line 119 [#FEF2F2]: `self.banner.setStyleSheet("#Card { background-color: #FEF2F2; border: 1px solid #FECACA; }")`
- Line 119 [#FECACA]: `self.banner.setStyleSheet("#Card { background-color: #FEF2F2; border: 1px solid #FECACA; }")`
- Line 120 [#991B1B]: `self.lbl_status.setStyleSheet("font-size: 13px; color: #991B1B; font-weight: bold;")`
- Line 160 [#0284C7]: `it.setForeground(QColor("#0284C7"))`
- Line 160 [QColor("#0284C7")]: `it.setForeground(QColor("#0284C7"))`

### app/ui/views/billing/return_view.py (8 occurrences)
- Line 112 [#1B1B18]: `lbl = QLabel("Returns"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 114 [#6B6558]: `ls = QLabel("Manage sales returns & purchase returns"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 132 [#6B6558]: `self.lbl_count = QLabel(""); self.lbl_count.setStyleSheet("color: #6B6558;")`
- Line 157 [#A6822E]: `cm = {"pending": "#A6822E", "approved": "#2F6844", "rejected": "#8B2635"}`
- Line 157 [#2F6844]: `cm = {"pending": "#A6822E", "approved": "#2F6844", "rejected": "#8B2635"}`
- Line 157 [#8B2635]: `cm = {"pending": "#A6822E", "approved": "#2F6844", "rejected": "#8B2635"}`
- Line 158 [#1B1B18]: `it_s.setForeground(QColor(cm.get(st, "#1B1B18"))); table.setItem(row, 4, it_s)`
- Line 158 [QColor(cm.get(st, "#1B1B18")]: `it_s.setForeground(QColor(cm.get(st, "#1B1B18"))); table.setItem(row, 4, it_s)`

### app/ui/views/gst_report_view.py (7 occurrences)
- Line 34 [#0284C7]: `self.card_taxable = StatCard("Taxable Turnover", "₹0.00", "Net value before tax", "#0284C7")`
- Line 35 [#10B981]: `self.card_cgst = StatCard("Total CGST", "₹0.00", "Central tax", "#10B981")`
- Line 36 [#10B981]: `self.card_sgst = StatCard("Total SGST", "₹0.00", "State tax", "#10B981")`
- Line 37 [#6366F1]: `self.card_igst = StatCard("Total IGST", "₹0.00", "Inter-state tax", "#6366F1")`
- Line 38 [#0F172A]: `self.card_total = StatCard("Total Invoice Value", "₹0.00", "Gross value", "#0F172A")`
- Line 155 [#0284C7]: `it.setForeground(QColor("#0284C7"))`
- Line 155 [QColor("#0284C7")]: `it.setForeground(QColor("#0284C7"))`

### app/ui/widgets/stat_card.py (7 occurrences)
- Line 10 [#1B1B18]: `def __init__(self, title: str, value: str, subtitle: str = "", value_color: str = "#1B1B18", parent=None):`
- Line 17 [#FBFBF9]: `background-color: #FBFBF9;`
- Line 18 [#D4C49E]: `border: 1px solid #D4C49E;`
- Line 29 [#6B6558]: `# Header / Title (12px, semi-bold, #6B6558, uppercase)`
- Line 32 [#6B6558]: `self.lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558; letter-spacing: 0.5px;")`
- Line 41 [#6B6558]: `# Subtitle / Hint (12px, regular, #6B6558)`
- Line 44 [#6B6558]: `self.lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`

### app/ui/views/billing/challan_view.py (7 occurrences)
- Line 58 [#1B1B18]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 133 [#1B1B18]: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 147 [#6B6558]: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 182 [#2C3E63]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas; padding: 4px 12px;")`
- Line 374 [#1B1B18]: `lbl = QLabel("Delivery Challans"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 376 [#6B6558]: `ls = QLabel("Create and track delivery challans"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 398 [#6B6558]: `self.lbl_count.setStyleSheet("color: #6B6558;")`

### app/ui/views/party_view.py (5 occurrences)
- Line 332 [#0284C7]: `it_cur.setForeground(QColor("#0284C7"))  # Receivable`
- Line 332 [QColor("#0284C7")]: `it_cur.setForeground(QColor("#0284C7"))  # Receivable`
- Line 334 [#D97706]: `it_cur.setForeground(QColor("#D97706"))  # Payable`
- Line 334 [QColor("#D97706")]: `it_cur.setForeground(QColor("#D97706"))  # Payable`
- Line 361 [#DC2626]: `btn_del.setStyleSheet("padding: 3px 8px; font-size: 11px; color: #DC2626;")`

### app/ui/views/expense_view.py (2 occurrences)
- Line 40 [#1B1B18]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 111 [#8B2635]: `self.lbl_total.setStyleSheet("font-family: Consolas, monospace; font-size: 14px; font-weight: bold; color: #8B2635;")`

### app/ui/views/daybook_view.py (1 occurrences)
- Line 81 [#1E293B]: `self.lbl_summary.setStyleSheet("font-size: 13px; color: #1E293B;")`

## 4. Hardcoded Fonts (`QFont`, `font-family`, `font-size`)

### app/ui/main_window.py (12 occurrences)
- Line 87 [font-size: 10px]: `section_bill.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 8px 8px 4px 8px;")`
- Line 87 [font-weight: 700]: `section_bill.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 8px 8px 4px 8px;")`
- Line 116 [font-size: 10px]: `section_acct.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")`
- Line 116 [font-weight: 700]: `section_acct.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")`
- Line 145 [font-size: 10px]: `section_sys.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")`
- Line 145 [font-weight: 700]: `section_sys.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")`
- Line 161 [font-size: 11px]: `self.lbl_lic_badge.setStyleSheet("color: #D4C49E; font-size: 11px; font-weight: 600; padding: 6px;")`
- Line 161 [font-weight: 600]: `self.lbl_lic_badge.setStyleSheet("color: #D4C49E; font-size: 11px; font-weight: 600; padding: 6px;")`
- Line 193 [font-size: 12px]: `self.lbl_clock.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569; background-color: #F1F5F9; padding: 4px 10px; border-radius: 4px;")`
- Line 193 [font-weight: 600]: `self.lbl_clock.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569; background-color: #F1F5F9; padding: 4px 10px; border-radius: 4px;")`
- Line 423 [font-size:14px]: `f"<b>System Health Status:</b> <span style='color: {status_color}; font-size:14px; font-weight:bold;'>{report['status']}</span><br/><br/>"`
- Line 423 [font-weight:bold]: `f"<b>System Health Status:</b> <span style='color: {status_color}; font-size:14px; font-weight:bold;'>{report['status']}</span><br/><br/>"`

### app/ui/views/billing/billing_reports_view.py (8 occurrences)
- Line 31 [font-size: 20px]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 31 [font-weight: 600]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 34 [font-size: 12px]: `ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 79 [font-size: 12px]: `lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 79 [font-weight: 600]: `lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 84 [font-size: 26px]: `lbl_value.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color}; font-family: Consolas;")`
- Line 84 [font-weight: bold]: `lbl_value.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color}; font-family: Consolas;")`
- Line 84 [font-family: Consolas]: `lbl_value.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color}; font-family: Consolas;")`

### app/ui/views/billing/challan_view.py (15 occurrences)
- Line 58 [font-size: 18px]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 58 [font-weight: 600]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 133 [font-size: 15px]: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 133 [font-weight: 600]: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 147 [font-size: 11px]: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 147 [font-weight: 600]: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 182 [font-size: 18px]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas; padding: 4px 12px;")`
- Line 182 [font-weight: bold]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas; padding: 4px 12px;")`
- Line 182 [font-family: Consolas]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas; padding: 4px 12px;")`
- Line 184 [font-family: Consolas]: `lbl.setStyleSheet("font-family: Consolas; font-size: 13px; padding: 4px 12px;")`
- Line 184 [font-size: 13px]: `lbl.setStyleSheet("font-family: Consolas; font-size: 13px; padding: 4px 12px;")`
- Line 374 [font-size: 20px]: `lbl = QLabel("Delivery Challans"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 374 [font-weight: 600]: `lbl = QLabel("Delivery Challans"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 376 [font-size: 12px]: `ls = QLabel("Create and track delivery challans"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 422 [QFont("Consolas", 10)]: `self.table.setRowCount(len(challans)); mono = QFont("Consolas", 10)`

### app/ui/views/billing/invoice_view.py (18 occurrences)
- Line 83 [font-family: Consolas]: `self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px;")`
- Line 83 [font-weight: bold]: `self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px;")`
- Line 83 [font-size: 13px]: `self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px;")`
- Line 90 [font-weight: bold]: `btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px;")`
- Line 193 [font-size: 18px]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 193 [font-weight: 600]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 290 [font-size: 15px]: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 290 [font-weight: 600]: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 304 [font-size: 11px]: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 304 [font-weight: 600]: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 338 [font-size: 18px]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63;")`
- Line 338 [font-weight: bold]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63;")`
- Line 340 [font-family: Consolas]: `lbl.setStyleSheet(lbl.styleSheet() + "font-family: Consolas; padding: 4px 12px;")`
- Line 556 [font-size: 20px]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 556 [font-weight: 600]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 559 [font-size: 12px]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 617 [font-size: 12px]: `self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 644 [QFont("Consolas", 10)]: `mono = QFont("Consolas", 10)`

### app/ui/views/billing/product_view.py (7 occurrences)
- Line 47 [font-size: 18px]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 47 [font-weight: 600]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 168 [font-size: 20px]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 168 [font-weight: 600]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 171 [font-size: 12px]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 254 [font-size: 12px]: `self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 274 [QFont("Consolas", 10)]: `mono = QFont("Consolas", 10)`

### app/ui/views/billing/proforma_view.py (13 occurrences)
- Line 62 [font-size: 18px]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 62 [font-weight: 600]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 159 [font-size: 15px]: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 159 [font-weight: 600]: `lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 173 [font-size: 11px]: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 173 [font-weight: 600]: `lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")`
- Line 206 [font-size: 18px]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63;")`
- Line 206 [font-weight: bold]: `self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63;")`
- Line 208 [font-family: Consolas]: `lbl.setStyleSheet(lbl.styleSheet() + "font-family: Consolas; padding: 4px 12px;")`
- Line 424 [font-size: 20px]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 424 [font-weight: 600]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 427 [font-size: 12px]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 505 [QFont("Consolas", 10)]: `mono = QFont("Consolas", 10)`

### app/ui/views/billing/purchase_order_view.py (11 occurrences)
- Line 33 [font-size: 18px]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;"); layout.addWidget(title)`
- Line 33 [font-weight: 600]: `title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;"); layout.addWidget(title)`
- Line 53 [font-size: 15px]: `lbl_items = QLabel("Items"); lbl_items.setStyleSheet("font-size: 15px; font-weight: 600;")`
- Line 53 [font-weight: 600]: `lbl_items = QLabel("Items"); lbl_items.setStyleSheet("font-size: 15px; font-weight: 600;")`
- Line 63 [font-size: 18px]: `self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas;")`
- Line 63 [font-weight: bold]: `self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas;")`
- Line 63 [font-family: Consolas]: `self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas;")`
- Line 122 [font-size: 20px]: `lbl = QLabel("Purchase Orders"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 122 [font-weight: 600]: `lbl = QLabel("Purchase Orders"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 124 [font-size: 12px]: `ls = QLabel("Create and track purchase orders to suppliers"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 160 [QFont("Consolas", 10)]: `self.table.setRowCount(len(pos)); mono = QFont("Consolas", 10)`

### app/ui/views/billing/quotation_view.py (19 occurrences)
- Line 94 [font-family: Consolas]: `self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px; color: #1B1B18;")`
- Line 94 [font-weight: bold]: `self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px; color: #1B1B18;")`
- Line 94 [font-size: 13px]: `self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px; color: #1B1B18;")`
- Line 101 [font-weight: bold]: `btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px; background: transparent;")`
- Line 187 [font-size: 18px]: `lbl_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 187 [font-weight: 600]: `lbl_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")`
- Line 195 [font-weight: 600]: `QTabBar::tab:selected { background: #FFFFFF; color: #1B1B18; font-weight: 600; border: 1px solid #D4C49E; border-bottom: none; }`
- Line 405 [font-family: Consolas]: `self.lbl_subtotal.setStyleSheet("font-family: Consolas; font-weight: 600; color: #1B1B18;")`
- Line 405 [font-weight: 600]: `self.lbl_subtotal.setStyleSheet("font-family: Consolas; font-weight: 600; color: #1B1B18;")`
- Line 410 [font-family: Consolas]: `self.lbl_tax.setStyleSheet("font-family: Consolas; font-weight: 600; color: #2C3E63;")`
- Line 410 [font-weight: 600]: `self.lbl_tax.setStyleSheet("font-family: Consolas; font-weight: 600; color: #2C3E63;")`
- Line 415 [font-family: Consolas]: `self.lbl_grand_total.setStyleSheet("font-family: Consolas; font-size: 15px; font-weight: bold; color: #2F6844;")`
- Line 415 [font-size: 15px]: `self.lbl_grand_total.setStyleSheet("font-family: Consolas; font-size: 15px; font-weight: bold; color: #2F6844;")`
- Line 415 [font-weight: bold]: `self.lbl_grand_total.setStyleSheet("font-family: Consolas; font-size: 15px; font-weight: bold; color: #2F6844;")`
- Line 606 [font-size: 20px]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 606 [font-weight: 600]: `lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 609 [font-size: 12px]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 693 [font-size: 12px]: `self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 728 [QFont("Consolas", 10)]: `mono = QFont("Consolas", 10)`

### app/ui/views/billing/return_view.py (6 occurrences)
- Line 62 [font-size: 18px]: `title.setStyleSheet("font-size: 18px; font-weight: 600;"); layout.addWidget(title)`
- Line 62 [font-weight: 600]: `title.setStyleSheet("font-size: 18px; font-weight: 600;"); layout.addWidget(title)`
- Line 112 [font-size: 20px]: `lbl = QLabel("Returns"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 112 [font-weight: 600]: `lbl = QLabel("Returns"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 114 [font-size: 12px]: `ls = QLabel("Manage sales returns & purchase returns"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 147 [QFont("Consolas", 10)]: `table.setRowCount(len(data)); mono = QFont("Consolas", 10)`

### app/ui/views/cashbank_view.py (7 occurrences)
- Line 39 [font-size: 20px]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 39 [font-weight: 700]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 145 [font-family: Consolas, monospace]: `self.lbl_summary.setStyleSheet("font-family: Consolas, monospace; font-size: 13px; font-weight: bold;")`
- Line 145 [font-size: 13px]: `self.lbl_summary.setStyleSheet("font-family: Consolas, monospace; font-size: 13px; font-weight: bold;")`
- Line 145 [font-weight: bold]: `self.lbl_summary.setStyleSheet("font-family: Consolas, monospace; font-size: 13px; font-weight: bold;")`
- Line 179 [QFont("Consolas", 12, QFont.Bold)]: `bal_item.setFont(QFont("Consolas", 12, QFont.Bold))`
- Line 239 [QFont("Consolas", 11, QFont.Bold)]: `bal_item.setFont(QFont("Consolas", 11, QFont.Bold))`

### app/ui/views/dashboard_view.py (28 occurrences)
- Line 67 [QFont("Consolas", 8)]: `painter.setFont(QFont("Consolas", 8))`
- Line 99 [QFont("Segoe UI", 9)]: `painter.setFont(QFont("Segoe UI", 9))`
- Line 109 [QFont("Segoe UI", 9, QFont.Bold)]: `painter.setFont(QFont("Segoe UI", 9, QFont.Bold))`
- Line 138 [font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif]: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 138 [font-size: 20px]: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 138 [font-weight: 600]: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 142 [font-family: 'Segoe UI', sans-serif]: `lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 142 [font-size: 12px]: `lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 182 [font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif]: `lbl_quick.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 182 [font-size: 15px]: `lbl_quick.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 182 [font-weight: 600]: `lbl_quick.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 236 [font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif]: `lbl_d.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 236 [font-size: 15px]: `lbl_d.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 236 [font-weight: 600]: `lbl_d.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 261 [font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif]: `lbl_s.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color:#8B2635;")`
- Line 261 [font-size: 15px]: `lbl_s.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color:#8B2635;")`
- Line 261 [font-weight: 600]: `lbl_s.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color:#8B2635;")`
- Line 287 [font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif]: `lbl_chart.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 287 [font-size: 15px]: `lbl_chart.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 287 [font-weight: 600]: `lbl_chart.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 307 [font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif]: `lbl_r.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 307 [font-size: 15px]: `lbl_r.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 307 [font-weight: 600]: `lbl_r.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 332 [font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif]: `lbl_i.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 332 [font-size: 15px]: `lbl_i.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 332 [font-weight: 600]: `lbl_i.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")`
- Line 369 [QFont("Consolas", 10)]: `mono_font = QFont("Consolas", 10)`
- Line 370 [QFont("Consolas", 10)]: `mono_bold = QFont("Consolas", 10)`

### app/ui/views/daybook_view.py (3 occurrences)
- Line 81 [font-size: 13px]: `self.lbl_summary.setStyleSheet("font-size: 13px; color: #1E293B;")`
- Line 131 [QFont()]: `font_bold = QFont()`
- Line 163 [font-size: 11px]: `btn_print.setStyleSheet("padding: 2px 6px; font-size: 11px;")`

### app/ui/views/expense_view.py (7 occurrences)
- Line 40 [font-size: 20px]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 40 [font-weight: 700]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 46 [font-size: 13px]: `btn_add.setStyleSheet("padding: 8px 18px; font-size: 13px;")`
- Line 111 [font-family: Consolas, monospace]: `self.lbl_total.setStyleSheet("font-family: Consolas, monospace; font-size: 14px; font-weight: bold; color: #8B2635;")`
- Line 111 [font-size: 14px]: `self.lbl_total.setStyleSheet("font-family: Consolas, monospace; font-size: 14px; font-weight: bold; color: #8B2635;")`
- Line 111 [font-weight: bold]: `self.lbl_total.setStyleSheet("font-family: Consolas, monospace; font-size: 14px; font-weight: bold; color: #8B2635;")`
- Line 166 [QFont("Consolas", 12, QFont.Bold)]: `total_item.setFont(QFont("Consolas", 12, QFont.Bold))`

### app/ui/views/gst_report_view.py (1 occurrences)
- Line 121 [QFont()]: `font_bold = QFont()`

### app/ui/views/ledger_view.py (30 occurrences)
- Line 38 [font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif]: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 38 [font-size: 20px]: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 38 [font-weight: 600]: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 42 [font-family: 'Segoe UI', sans-serif]: `lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 42 [font-size: 12px]: `lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 55 [font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif]: `lbl_p.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 55 [font-size: 12px]: `lbl_p.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 55 [font-weight: 600]: `lbl_p.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 64 [font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif]: `lbl_from.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 64 [font-size: 12px]: `lbl_from.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 64 [font-weight: 600]: `lbl_from.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 74 [font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif]: `lbl_to.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 74 [font-size: 12px]: `lbl_to.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 74 [font-weight: 600]: `lbl_to.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")`
- Line 118 [font-size: 13px]: `self.lbl_p_info.setStyleSheet("font-size: 13px; color: #1B1B18; line-height: 1.4;")`
- Line 128 [font-size: 12px]: `self.lbl_bal_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 133 [font-family: 'Consolas', 'Cascadia Mono', monospace]: `self.lbl_bal_headline.setStyleSheet("font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: #6B6558;")`
- Line 133 [font-size: 24px]: `self.lbl_bal_headline.setStyleSheet("font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: #6B6558;")`
- Line 133 [font-weight: bold]: `self.lbl_bal_headline.setStyleSheet("font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: #6B6558;")`
- Line 191 [font-family: \]: `f"<span style='font-family: \"Bahnschrift\", \"Segoe UI Semibold\", sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;'>{p['name']}</span> "`
- Line 191 [font-size: 15px]: `f"<span style='font-family: \"Bahnschrift\", \"Segoe UI Semibold\", sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;'>{p['name']}</span> "`
- Line 191 [font-weight: 600]: `f"<span style='font-family: \"Bahnschrift\", \"Segoe UI Semibold\", sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;'>{p['name']}</span> "`
- Line 192 [font-size: 12px]: `f"<span style='font-size: 12px; color: #6B6558;'>({location or 'Local'})</span><br/>"`
- Line 193 [font-size: 12px]: `f"<span style='font-size: 12px; color: #6B6558;'>GSTIN: {gst_str} | Phone: {phone_str} | Credit Period: {p.get('credit_period_days', 30)} Days</span>"`
- Line 213 [font-family: 'Consolas', 'Cascadia Mono', monospace]: `self.lbl_bal_headline.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: {cl_color};")`
- Line 213 [font-size: 24px]: `self.lbl_bal_headline.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: {cl_color};")`
- Line 213 [font-weight: bold]: `self.lbl_bal_headline.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: {cl_color};")`
- Line 223 [QFont("Consolas", 10)]: `font_mono = QFont("Consolas", 10)`
- Line 224 [QFont("Consolas", 10)]: `font_mono_bold = QFont("Consolas", 10)`
- Line 227 [QFont("Bahnschrift", 10)]: `font_hdr_bold = QFont("Bahnschrift", 10)`

### app/ui/views/outstanding_view.py (12 occurrences)
- Line 149 [QFont()]: `font_bold = QFont()`
- Line 201 [font-size: 11px]: `btn_led.setStyleSheet("padding: 2px 6px; font-size: 11px;")`
- Line 206 [font-size: 11px]: `btn_rem.setStyleSheet("padding: 2px 8px; font-size: 11px; font-weight: 600; color: #2F6844; border: 1px solid #2F6844; border-radius: 3px;")`
- Line 206 [font-weight: 600]: `btn_rem.setStyleSheet("padding: 2px 8px; font-size: 11px; font-weight: 600; color: #2F6844; border: 1px solid #2F6844; border-radius: 3px;")`
- Line 326 [font-size: 14px]: `lbl_party.setStyleSheet("font-size: 14px; color: #1B1B18;")`
- Line 330 [font-size: 15px]: `lbl_due = QLabel(f"<b>Total Outstanding Balance:</b> <span style='color: #8B2635; font-size: 15px; font-weight: bold;'>₹{tot:,.2f}</span>")`
- Line 330 [font-weight: bold]: `lbl_due = QLabel(f"<b>Total Outstanding Balance:</b> <span style='color: #8B2635; font-size: 15px; font-weight: bold;'>₹{tot:,.2f}</span>")`
- Line 362 [font-family: Consolas, monospace]: `self.txt_message.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background-color: #FFFFFF; color: #1B1B18; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px;")`
- Line 362 [font-size: 12px]: `self.txt_message.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background-color: #FFFFFF; color: #1B1B18; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px;")`
- Line 370 [font-size: 12px]: `btn_copy.setStyleSheet("padding: 8px 16px; font-size: 12px;")`
- Line 382 [font-weight: bold]: `btn_send_wa.setStyleSheet("background-color: #2F6844; color: #FFFFFF; font-weight: bold; padding: 8px 20px; font-size: 13px; border-radius: 4px;")`
- Line 382 [font-size: 13px]: `btn_send_wa.setStyleSheet("background-color: #2F6844; color: #FFFFFF; font-weight: bold; padding: 8px 20px; font-size: 13px; border-radius: 4px;")`

### app/ui/views/party_view.py (3 occurrences)
- Line 351 [font-size: 11px]: `btn_led.setStyleSheet("padding: 3px 8px; font-size: 11px;")`
- Line 356 [font-size: 11px]: `btn_edit.setStyleSheet("padding: 3px 8px; font-size: 11px;")`
- Line 361 [font-size: 11px]: `btn_del.setStyleSheet("padding: 3px 8px; font-size: 11px; color: #DC2626;")`

### app/ui/views/pnl_view.py (16 occurrences)
- Line 61 [QFont("Consolas", 8)]: `painter.setFont(QFont("Consolas", 8))`
- Line 88 [QFont("Segoe UI", 9, QFont.Bold)]: `painter.setFont(QFont("Segoe UI", 9, QFont.Bold))`
- Line 92 [QFont("Segoe UI", 9)]: `painter.setFont(QFont("Segoe UI", 9))`
- Line 123 [font-size: 20px]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 123 [font-weight: 700]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 170 [font-size: 14px]: `lbl_stmt.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63; letter-spacing: 1px;")`
- Line 170 [font-weight: 700]: `lbl_stmt.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63; letter-spacing: 1px;")`
- Line 191 [font-size: 13px]: `lbl_chart.setStyleSheet("font-size: 13px; font-weight: 600; color: #2C3E63;")`
- Line 191 [font-weight: 600]: `lbl_chart.setStyleSheet("font-size: 13px; font-weight: 600; color: #2C3E63;")`
- Line 201 [font-size: 14px]: `self.lbl_gross_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2F6844;")`
- Line 201 [font-weight: 700]: `self.lbl_gross_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2F6844;")`
- Line 203 [font-size: 14px]: `self.lbl_net_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63;")`
- Line 203 [font-weight: 700]: `self.lbl_net_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63;")`
- Line 262 [QFont("Segoe UI", 12, QFont.Bold)]: `lbl_item.setFont(QFont("Segoe UI", 12, QFont.Bold))`
- Line 272 [QFont("Consolas", 13, QFont.Bold)]: `amt_item.setFont(QFont("Consolas", 13, QFont.Bold))`
- Line 278 [QFont("Consolas", 12)]: `amt_item.setFont(QFont("Consolas", 12))`

### app/ui/views/settings_view.py (12 occurrences)
- Line 109 [font-size: 11px]: `self.lbl_logo_path.setStyleSheet("color: #64748B; font-size: 11px;")`
- Line 128 [font-size: 13px]: `btn_save.setStyleSheet("padding: 8px 24px; font-size: 13px;")`
- Line 222 [font-size: 13px]: `lbl_info.setStyleSheet("font-size: 13px; color: #1E293B;")`
- Line 341 [font-size: 13px]: `self.lbl_lic_status.setStyleSheet("font-size: 13px; color: #0F172A;")`
- Line 354 [font-family: monospace]: `self.lbl_m_val.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: bold; color: #0284C7;")`
- Line 354 [font-size: 13px]: `self.lbl_m_val.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: bold; color: #0284C7;")`
- Line 354 [font-weight: bold]: `self.lbl_m_val.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: bold; color: #0284C7;")`
- Line 356 [font-size: 11px]: `btn_copy_m.setStyleSheet("padding: 4px 10px; font-size: 11px;")`
- Line 375 [font-size: 13px]: `btn_activate.setStyleSheet("padding: 8px 24px; font-size: 13px;")`
- Line 411 [font-size: 13px]: `self.lbl_health_info.setStyleSheet("font-size: 13px; line-height: 1.5; color: #1E293B;")`
- Line 461 [QFont("Consolas", 9)]: `self.txt_log_content.setFont(QFont("Consolas", 9))`
- Line 477 [font-weight:bold]: `f"<b>Status:</b> <span style='color: {status_col}; font-weight:bold;'>{report['status']}</span> | "`

### app/ui/views/stock_report_view.py (10 occurrences)
- Line 42 [font-size: 20px]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 42 [font-weight: 700]: `lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")`
- Line 44 [font-size: 12px]: `lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")`
- Line 51 [font-size: 12px]: `btn_export.setStyleSheet("padding: 7px 14px; font-size: 12px;")`
- Line 57 [font-size: 12px]: `btn_refresh.setStyleSheet("padding: 7px 16px; font-size: 12px;")`
- Line 88 [font-size: 12px]: `lbl_range.setStyleSheet("color: #1B1B18; font-size: 12px;")`
- Line 100 [font-size: 12px]: `lbl_from.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 108 [font-size: 12px]: `lbl_to.setStyleSheet("color: #6B6558; font-size: 12px;")`
- Line 132 [font-size: 12px]: `btn_apply.setStyleSheet("padding: 4px 12px; font-size: 12px;")`
- Line 268 [QFont()]: `font_bold = QFont()`

### app/ui/views/trial_balance_view.py (7 occurrences)
- Line 73 [font-size: 14px]: `self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")`
- Line 73 [font-weight: bold]: `self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")`
- Line 113 [font-size: 13px]: `self.lbl_status.setStyleSheet("font-size: 13px; color: #065F46; font-weight: bold;")`
- Line 113 [font-weight: bold]: `self.lbl_status.setStyleSheet("font-size: 13px; color: #065F46; font-weight: bold;")`
- Line 120 [font-size: 13px]: `self.lbl_status.setStyleSheet("font-size: 13px; color: #991B1B; font-weight: bold;")`
- Line 120 [font-weight: bold]: `self.lbl_status.setStyleSheet("font-size: 13px; color: #991B1B; font-weight: bold;")`
- Line 126 [QFont()]: `font_bold = QFont()`

### app/ui/views/voucher_view.py (10 occurrences)
- Line 127 [font-size: 12px]: `self.lbl_party_balance.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 6px 10px; border-radius: 4px; color: #475569; font-size: 12px;")`
- Line 219 [font-size: 12px]: `self.lbl_taxable.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 221 [font-size: 12px]: `self.lbl_cgst.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 223 [font-size: 12px]: `self.lbl_sgst.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 225 [font-size: 12px]: `self.lbl_igst.setStyleSheet("font-size: 12px; color: #475569;")`
- Line 227 [font-size: 16px]: `self.lbl_grand_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284C7; padding-top: 4px; border-top: 1px dashed #CBD5E1;")`
- Line 227 [font-weight: bold]: `self.lbl_grand_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284C7; padding-top: 4px; border-top: 1px dashed #CBD5E1;")`
- Line 244 [font-size: 14px]: `self.btn_save.setStyleSheet("padding: 8px 24px; font-size: 14px;")`
- Line 250 [font-size: 14px]: `self.btn_save_print.setStyleSheet("padding: 8px 20px; font-size: 14px;")`
- Line 347 [font-size:11px]: `btn_del.setStyleSheet("border:none; padding:2px; font-size:11px;")`

### app/ui/widgets/stat_card.py (8 occurrences)
- Line 32 [font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif]: `self.lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558; letter-spacing: 0.5px;")`
- Line 32 [font-size: 12px]: `self.lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558; letter-spacing: 0.5px;")`
- Line 32 [font-weight: 600]: `self.lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558; letter-spacing: 0.5px;")`
- Line 38 [font-family: 'Consolas', 'Cascadia Mono', 'Courier New', monospace]: `self.lbl_value.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', 'Courier New', monospace; font-size: 24px; font-weight: bold; color: {value_color};")`
- Line 38 [font-size: 24px]: `self.lbl_value.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', 'Courier New', monospace; font-size: 24px; font-weight: bold; color: {value_color};")`
- Line 38 [font-weight: bold]: `self.lbl_value.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', 'Courier New', monospace; font-size: 24px; font-weight: bold; color: {value_color};")`
- Line 44 [font-family: 'Segoe UI', sans-serif]: `self.lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 44 [font-size: 12px]: `self.lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`

## 5. Icon Sources & Emojis Used as Icons

### app/ui/main_window.py
- Line 61: '"sidebar_logo.jpg"'

### app/ui/views/billing/invoice_view.py
- Line 88: '✕'

### app/ui/views/billing/quotation_view.py
- Line 99: '✕'

### app/ui/views/cashbank_view.py
- Line 38: '🏦'
- Line 43: '➕'
- Line 49: '📝'
- Line 73: '📊'
- Line 78: '📖'
- Line 122: '🔍'
- Line 149: '🗑'

### app/ui/views/daybook_view.py
- Line 61: '🔍'
- Line 68: '📊'
- Line 162: '🖨'

### app/ui/views/expense_view.py
- Line 38: '💰'
- Line 44: '➕'
- Line 50: '📁'
- Line 87: '🔍'
- Line 115: '🗑'
- Line 332: '➕'

### app/ui/views/gst_report_view.py
- Line 70: '🔍'
- Line 77: '📊'
- Line 219: '📤'
- Line 220: '📥'

### app/ui/views/outstanding_view.py
- Line 65: '🔍'
- Line 81: '🔄'
- Line 85: '📄'
- Line 90: '📊'
- Line 205: '💬'
- Line 267: '📥'
- Line 268: '📤'
- Line 282: '💬'
- Line 369: '📋'
- Line 380: '🚀'
- Line 406: '📊'
- Line 411: '💳'
- Line 418: '⚠'
- Line 423: '💳'
- Line 433: '💳'
- Line 440: '⚠'
- Line 445: '💳'

### app/ui/views/party_view.py
- Line 250: '🔍'
- Line 266: '➕'

### app/ui/views/pnl_view.py
- Line 122: '📊'
- Line 141: '📈'

### app/ui/views/settings_view.py
- Line 40: '🏢'
- Line 45: '💾'
- Line 50: '🔑'
- Line 55: '🩺'
- Line 110: '📁'
- Line 112: '❌'
- Line 126: '💾'
- Line 230: '📦'
- Line 236: '🔄'
- Line 241: '🌱'
- Line 247: '🗑'
- Line 355: '📋'
- Line 373: '⚡'
- Line 419: '🩺'
- Line 425: '🧵'
- Line 430: '📁'
- Line 452: '🔄'

### app/ui/views/stock_report_view.py
- Line 41: '📦'
- Line 50: '📊'
- Line 55: '🔄'
- Line 117: '🔍'

### app/ui/views/trial_balance_view.py
- Line 53: '🔍'
- Line 60: '📊'
- Line 110: '✅'
- Line 117: '⚠'

### app/ui/views/voucher_view.py
- Line 73: '🔄'
- Line 137: '📦'
- Line 140: '➕'
- Line 242: '💾'
- Line 248: '🖨'
- Line 346: '❌'

## 6. Dashboard Charts & Custom Paint Colors
- Line 10: `from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPixmap`
- Line 18: `"""Custom flat QPainter bar chart showing 6-month comparison in Ink Indigo & Ledger Brass."""`
- Line 22: `self.data = []  # list of {"month_short", "sales", "purchases"}`
- Line 30: `def paintEvent(self, event):`
- Line 33: `painter = QPainter(self)`
- Line 34: `painter.setRenderHint(QPainter.Antialiasing)`
- Line 50: `# Find max value for scale`
- Line 59: `# Draw Y-axis gridlines and labels (#D4C49E brass ruled line, #6B6558 muted text)`
- Line 60: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 64: `painter.drawLine(int(margin_left), int(y_pos), int(w - margin_right), int(y_pos))`
- Line 66: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 74: `painter.drawText(QRect(0, int(y_pos) - 8, margin_left - 8, 16), Qt.AlignRight | Qt.AlignVCenter, label)`
- Line 75: `painter.setPen(QPen(QColor("#D4C49E"), 1))`
- Line 77: `# Draw Flat Solid Bars (No gradients, flat ink & brass)`
- Line 81: `# Debits bar: Solid #2C3E63 (Ink Indigo)`
- Line 85: `painter.setBrush(QBrush(QColor("#2C3E63")))`
- Line 86: `painter.setPen(Qt.NoPen)`
- Line 87: `painter.drawRect(QRectF(s_x, s_y, bar_w, s_height))`
- Line 89: `# Credits bar: Solid #A6822E (Ledger Brass)`
- Line 93: `painter.setBrush(QBrush(QColor("#A6822E")))`
- Line 94: `painter.setPen(Qt.NoPen)`
- Line 95: `painter.drawRect(QRectF(p_x, p_y, bar_w, p_height))`
- Line 97: `# Month label (12px, #6B6558)`
- Line 98: `painter.setPen(QPen(QColor("#6B6558"), 1))`
- Line 101: `painter.drawText(lbl_rect, Qt.AlignHCenter | Qt.AlignTop, d["month_short"])`
- Line 103: `# Legend (Top right, flat swatches)`
- Line 105: `painter.setPen(Qt.NoPen)`
- Line 106: `painter.setBrush(QColor("#2C3E63"))`
- Line 107: `painter.drawRect(int(margin_left), legend_y, 12, 12)`
- Line 108: `painter.setPen(QColor("#1B1B18"))`
- Line 110: `painter.drawText(int(margin_left + 16), legend_y + 10, "Debits")`
- Line 112: `painter.setPen(Qt.NoPen)`
- Line 113: `painter.setBrush(QColor("#A6822E"))`
- Line 114: `painter.drawRect(int(margin_left + 80), legend_y, 12, 12)`
- Line 115: `painter.setPen(QColor("#1B1B18"))`
- Line 116: `painter.drawText(int(margin_left + 96), legend_y + 10, "Credits")`
- Line 122: `navigate_to = Signal(str, dict)  # view_name, params`
- Line 131: `main_layout.setSpacing(24)  # 24px space between major sections (8px grid)`
- Line 133: `# 1. Screen Title Header`
- Line 138: `lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")`
- Line 142: `lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")`
- Line 147: `# 2. KPI Rows`
- Line 148: `# Row 1: Billing & Inventory KPIs`
- Line 151: `self.card_inv_amt = StatCard("Today's Sales (Invoices)", "₹0.00", "Total sales today", value_color="#2F6844")`
- Line 152: `self.card_inv_cnt = StatCard("Invoices Today", "0", "Count of invoices", value_color="#1B1B18")`
- Line 153: `self.card_prof = StatCard("Pending Quotations", "0", "Sent proformas", value_color="#A6822E")`
- Line 154: `self.card_stock = StatCard("Low Stock Alerts", "0", "Items needing reorder", value_color="#8B2635")`
- Line 161: `# Row 2: Accounting KPIs`
- Line 164: `self.card_rec = StatCard("Total Receivables (Debtors)", "₹0.00", "Money owed to you", value_color="#2F6844")`
- Line 165: `self.card_pay = StatCard("Total Payables (Creditors)", "₹0.00", "Money you owe", value_color="#8B2635")`
- Line 166: `self.card_sales = StatCard("Today's Debits", "₹0.00", "Billed today", value_color="#2C3E63")`
- Line 167: `self.card_rec_today = StatCard("Today's Collections", "₹0.00", "Collected today", value_color="#1B1B18")`
- Line 174: `# 3. Quick Action Toolbar`
- Line 182: `lbl_quick.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;")`
- Line 220: `# 4. Three Column Grid`
- Line 224: `# --- LEFT COLUMN (Debtors & Low Stock) ---`
- Line 228: `# Top Debtors`
- Line 253: `# Low Stock`
- Line 261: `lbl_s.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color:#8B2635;")`
- Line 280: `# --- CENTER COLUMN (Trend Chart) ---`
- Line 295: `# --- RIGHT COLUMN (Vouchers & Invoices) ---`
- Line 299: `# Recent Vouchers`
- Line 324: `# Recent Invoices`
- Line 339: `self.tbl_invoices.setHorizontalHeaderLabels(["Date", "Inv #", "Party", "Amount"])`
- Line 364: `self.card_prof.set_value(str(kpi.get('pending_proformas_count', 0)))`
- Line 373: `# Debtors`
- Line 382: `it_amt.setForeground(QColor("#2F6844"))`
- Line 388: `# Low Stock`
- Line 395: `it_stock.setForeground(QColor("#8B2635"))`
- Line 403: `# Recent Vouchers`
- Line 420: `# Recent Invoices`

## 7. Export Colors (PDF & Excel Exports)

### app/services/billing/challan_pdf_generator.py (13 occurrences)
- Line 23 [#1B4F72]: `self.primary_color = colors.HexColor('#1B4F72')        # Professional Navy`
- Line 24 [#0F2C59]: `self.primary_dark = colors.HexColor('#0F2C59')         # Deep Navy`
- Line 25 [#EBF3FB]: `self.primary_light = colors.HexColor('#EBF3FB')        # Soft Ice Blue highlight`
- Line 26 [#F8FAFC]: `self.bg_light = colors.HexColor('#F8FAFC')             # Slate 50`
- Line 27 [#CBD5E1]: `self.border_color = colors.HexColor('#CBD5E1')         # Slate 300`
- Line 28 [#E2E8F0]: `self.border_subtle = colors.HexColor('#E2E8F0')        # Slate 200`
- Line 29 [#1E293B]: `self.text_dark = colors.HexColor('#1E293B')            # Slate 800`
- Line 30 [#64748B]: `self.text_muted = colors.HexColor('#64748B')           # Slate 500`
- Line 125 [#334155]: `fontSize=7.5, fontName='Helvetica', textColor=colors.HexColor('#334155'),`
- Line 155 [#334155]: `fontSize=7, fontName='Helvetica-Bold', textColor=colors.HexColor('#334155'), leading=9`
- Line 166 [#94A3B8]: `fontSize=6.5, fontName='Helvetica', textColor=colors.HexColor('#94A3B8'),`
- Line 366 [#64748B]: `desc += f"<br/><font size=\"6.5\" color=\"#64748B\">{item.get('description')}</font>"`
- Line 454 [#F1F5F9]: `('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),`

### app/services/billing/quotation_pdf_generator.py (22 occurrences)
- Line 56 [#0F2942]: `self.setFillColor(colors.HexColor('#0F2942'))`
- Line 60 [#D97706]: `self.setFillColor(colors.HexColor('#D97706'))`
- Line 84 [#0F2942]: `Features executive navy (#0F2942) and gold (#D97706) styling, balanced full-page`
- Line 84 [#D97706]: `Features executive navy (#0F2942) and gold (#D97706) styling, balanced full-page`
- Line 92 [#0F2942]: `self.c_primary = colors.HexColor('#0F2942')       # Deep Executive Navy`
- Line 93 [#EBF3FA]: `self.c_primary_light = colors.HexColor('#EBF3FA') # Soft Ice Blue`
- Line 94 [#1E40AF]: `self.c_secondary = colors.HexColor('#1E40AF')     # Royal Slate Blue`
- Line 95 [#D97706]: `self.c_accent = colors.HexColor('#D97706')        # Warm Champagne Gold / Amber`
- Line 96 [#FEF3C7]: `self.c_accent_light = colors.HexColor('#FEF3C7')  # Soft Amber Tint`
- Line 97 [#B45309]: `self.c_accent_dark = colors.HexColor('#B45309')   # Rich Amber Text`
- Line 98 [#1E293B]: `self.c_dark = colors.HexColor('#1E293B')          # Slate 800 (Main text)`
- Line 99 [#64748B]: `self.c_muted = colors.HexColor('#64748B')         # Slate 500 (Subtext)`
- Line 100 [#F8FAFC]: `self.c_light_bg = colors.HexColor('#F8FAFC')      # Slate 50 background`
- Line 101 [#CBD5E1]: `self.c_border = colors.HexColor('#CBD5E1')        # Slate 300 border`
- Line 102 [#E2E8F0]: `self.c_border_subtle = colors.HexColor('#E2E8F0') # Slate 200 border`
- Line 103 [#15803D]: `self.c_success = colors.HexColor('#15803D')       # Emerald Green`
- Line 104 [#DCFCE7]: `self.c_success_light = colors.HexColor('#DCFCE7') # Soft Emerald Tint`
- Line 392 [#B45309]: `right_header.append(Paragraph(f"<b>Offer Valid Until:</b> <font color='#B45309'><b>{valid_until}</b></font>", self.styles['QValidityBadge']))`
- Line 556 [#CBD5E1]: `Paragraph(f"<font color='#CBD5E1'>{fill_idx}</font>", self.styles['QItemCellCenter']),`
- Line 557 [#E2E8F0]: `Paragraph("<font color='#E2E8F0'>—</font>", self.styles['QItemCellCenter']),`
- Line 669 [#15803D]: `Paragraph("<font color='#15803D'>Client Discount Saved:</font>", self.styles['QSummaryLabel']),`
- Line 670 [#15803D]: `Paragraph(f"<font color='#15803D'>- Rs. {float(total_discount_savings):,.2f}</font>", self.styles['QSummaryVal'])`

### app/services/export_service.py (48 occurrences)
- Line 92 [#64748B]: `self.setFillColor(colors.HexColor("#64748B"))`
- Line 95 [#E2E8F0]: `self.setStrokeColor(colors.HexColor("#E2E8F0"))`
- Line 151 [#0F172A]: `textColor=colors.HexColor('#0F172A')`
- Line 156 [#475569]: `textColor=colors.HexColor('#475569')`
- Line 161 [#1E293B]: `textColor=colors.HexColor('#1E293B'), alignment=1`
- Line 166 [#0F172A]: `textColor=colors.HexColor('#0F172A')`
- Line 171 [#1E293B]: `textColor=colors.HexColor('#1E293B')`
- Line 192 [#475569]: `f"<font size=8.5 color='#475569'>{comp_addr}, {comp.get('city', '')} - {comp.get('pincode', '')}, {comp.get('state', '')}</font>",`
- Line 225 [#0284C7]: `story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=8))`
- Line 232 [#64748B]: `story.append(Paragraph(f"<font size=8 color='#64748B'>{date_str}</font>", ParagraphStyle('SubDate', alignment=1)))`
- Line 255 [#0284C7]: `f"<b>Closing Balance:</b> <font color='#0284C7'><b>₹{cl_amt:,.2f} {cl_type}</b></font>",`
- Line 262 [#F8FAFC]: `('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),`
- Line 263 [#CBD5E1]: `('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),`
- Line 303 [#64748B]: `v_ref += f"<br/><font size=7 color='#64748B'>Ref: {row['reference_no']}</font>"`
- Line 335 [#0F172A]: `('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),`
- Line 338 [#E2E8F0]: `('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),`
- Line 339 [#F8FAFC]: `('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F8FAFC')]),`
- Line 340 [#E2E8F0]: `('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),`
- Line 386 [#0F172A]: `title_style = ParagraphStyle('T1', fontName='Helvetica-Bold', fontSize=14, leading=16, textColor=colors.HexColor('#0F172A'))`
- Line 387 [#475569]: `sub_style = ParagraphStyle('S1', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#475569'))`
- Line 388 [#1E293B]: `cell_style = ParagraphStyle('C1', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'))`
- Line 430 [#CBD5E1]: `story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=6))`
- Line 446 [#F8FAFC]: `('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),`
- Line 447 [#CBD5E1]: `('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),`
- Line 498 [#0F172A]: `('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")),`
- Line 499 [#CBD5E1]: `('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),`
- Line 524 [#0F172A]: `('LINEABOVE', (1,-1), (2,-1), 1, colors.HexColor("#0F172A")),`
- Line 569 [#0F172A]: `title_style = ParagraphStyle('OTitle', fontName='Helvetica-Bold', fontSize=14, leading=16, textColor=colors.HexColor('#0F172A'))`
- Line 570 [#475569]: `sub_style = ParagraphStyle('OSub', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#475569'))`
- Line 571 [#1E293B]: `cell_style = ParagraphStyle('OCell', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'))`
- Line 575 [#1E293B]: `heading_style = ParagraphStyle('OHead', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#1E293B'), alignment=1)`
- Line 585 [#475569]: `f"<font size=8.5 color='#475569'>{comp.get('address', '')}, {comp.get('city', '')} - {comp.get('pincode', '')}, {comp.get('state', '')}</font>",`
- Line 611 [#0284C7]: `story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=8))`
- Line 617 [#64748B]: `story.append(Paragraph(f"<font size=8 color='#64748B'>{date_str} | {report_data.get('party_count', 0)} Parties</font>", ParagraphStyle('SubD', alignment=1)))`
- Line 661 [#0F172A]: `('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),`
- Line 664 [#E2E8F0]: `('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),`
- Line 665 [#F8FAFC]: `('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F8FAFC')]),`
- Line 666 [#E2E8F0]: `('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),`
- Line 702 [#1E293B]: `cell_style = ParagraphStyle('DBCell', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'))`
- Line 704 [#1E293B]: `heading_style = ParagraphStyle('DBHead', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#1E293B'), alignment=1)`
- Line 707 [#64748B]: `Paragraph(f"<font size=8 color='#64748B'>Period: {daybook_data['from_date']} to {daybook_data['to_date']}</font>", ParagraphStyle('DBSub', alignment=1)),`
- Line 732 [#0F172A]: `('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),`
- Line 734 [#E2E8F0]: `('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),`
- Line 755 [#1E293B]: `cell_style = ParagraphStyle('TBCell', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'))`
- Line 757 [#1E293B]: `heading_style = ParagraphStyle('TBHead', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#1E293B'), alignment=1)`
- Line 760 [#64748B]: `Paragraph(f"<font size=8 color='#64748B'>As of {tb_data.get('to_date')}</font>", ParagraphStyle('TBSub', alignment=1)),`
- Line 786 [#0F172A]: `('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),`
- Line 788 [#E2E8F0]: `('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),`
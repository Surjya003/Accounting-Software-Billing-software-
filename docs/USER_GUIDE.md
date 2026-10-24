# BillFlow Suite — Comprehensive User Guide

**Application Version:** 1.0.0 (Production Release)  
**Target Audience:** Business Owners, Accountants, Cashiers, Billing Operators  

---

## 1. Getting Started & Navigation

### 1.1 First Launch & Company Profile Setup
Upon initial launch, configure your business details in **Settings (F12)** > **🏢 Company Profile & Print Settings**:
1. **Legal Business Name & Trade Name**: Appears at the top of all printed invoices, quotations, and reports.
2. **GSTIN (Goods and Services Tax Identification Number)**: Ensure the 15-character GSTIN is entered accurately. The first 2 digits automatically determine your Home State Code (e.g., `19` for West Bengal, `27` for Maharashtra).
3. **State and State Code**: Used for automatic tax calculation:
   - Same State = **CGST + SGST** (Intra-state supply)
   - Different State = **IGST** (Inter-state supply)
4. **Complete Postal Address, Phone, and Email**: Printed in the header banner.
5. **Bank Account Details**: Beneficiary name, bank name, account number, and IFSC code for buyer payment transfers.
6. **Company Logo & Seal/Signature**: Upload PNG/JPEG images (auto-scaled and centered in invoice headers and signature blocks).

---

## 2. Keyboard Shortcuts Quick Reference Card

BillFlow Suite is designed for rapid, mouse-free commercial keyboard navigation:

| Key | Action / View | Description |
| :---: | :--- | :--- |
| **F1** | 📊 **Dashboard** | Executive overview: Sales, receivables, payables, low-stock alerts, monthly charts |
| **F2** | 👥 **Parties / Ledgers** | Customer and Supplier directories, opening balances, credit limits |
| **F3** | 📦 **Products / Inventory** | Item master, SKU, HSN codes, buying/selling prices, stock adjustments |
| **F4** | 📝 **Quotations / Estimates** | Cost estimates, validity periods, one-click conversion to Tax Invoice |
| **F5** | 🧾 **Tax Invoices** | GST tax invoices, itemized tax rates, e-way bill details, print PDF |
| **F6** | 🚚 **Delivery Challans** | Non-financial goods movement under Rule 55 (job work, demo, approval) |
| **F7** | 🛒 **Purchase Orders** | Supplier procurement orders, receiving goods, and purchase returns |
| **F8** | 🔄 **Sales Returns (CN)** | Credit notes, stock restoration, linked invoice adjustments |
| **F9** | 📅 **Daybook** | Daily journal of all debits, credits, invoices, vouchers, and cash flow |
| **F10** | 💵 **Cash & Bank** | Cash receipts, bank deposits, contra transfers, payments |
| **F11** | 📈 **GST Reports** | GSTR-1 outward sales, GSTR-3B ITC, Government Offline JSON Tool export |
| **F12** | ⚙️ **Settings & Preferences** | Company profile, database backups, themes, offline licensing |
| **Ctrl + S** | **Save Record** | Save current active form (Invoice, Party, Product, Voucher) |
| **Ctrl + P** | **Print / Export PDF** | Generate high-resolution ReportLab PDF |
| **Esc** | **Close / Cancel** | Close active dialog or cancel current input |

---

## 3. Party & Ledger Management

### 3.1 Creating Customers and Suppliers
Navigate to **Parties (F2)** > Click **"+ Add Party"**:
- **Party Type**: Select *Customer*, *Supplier*, or *Both*.
- **Party Name & Code**: Unique trading identity.
- **GSTIN & PAN**: When entering GSTIN, the state code is automatically extracted. Unregistered parties should have GSTIN left blank or set to `URP`.
- **Billing & Shipping Addresses**: Enter distinct delivery locations if consignee differs from buyer.
- **Opening Balance**: Enter prior balance with type:
  - **Dr (Receivable)**: Customer owes us money.
  - **Cr (Payable)**: We owe supplier money.
- **Credit Limit & Terms**: Credit period in days and maximum credit limit in Rupees.

### 3.2 Outstanding & Overdue Ageing Reports
Under **Parties** > **Outstanding Receivables**:
- View real-time age analysis segmented into standard brackets:
  - **0–30 Days** (Current)
  - **31–60 Days** (Mild Overdue)
  - **61–90 Days** (Substantial Overdue)
  - **90+ Days** (Critical Overdue)
- Click **"WhatsApp Reminder"** to copy pre-formatted collection reminders with bank details to clipboard.

---

## 4. Sales & Billing Workflow

### 4.1 Quotations (F4)
1. Select customer and validity period (e.g., 30 days).
2. Add line items with HSN codes, quantity, unit price, and GST rate.
3. Once accepted by buyer, click **"Convert to Tax Invoice"** to automatically transfer all lines, quantities, and pricing into an active invoice without re-typing.

### 4.2 Creating a Tax Invoice (F5)
1. Press **F5** > Click **"+ Create Invoice"**.
2. **Select Customer**: Address, State, and GSTIN populate automatically.
3. **Place of Supply**: Verified against customer state. If inter-state, IGST applies; if intra-state, CGST and SGST apply.
4. **Line Items**: Type product name or scan barcode. Rate, HSN code, and GST slab are pulled from product master.
5. **Reverse Charge**: Toggle YES if tax is payable by recipient under Section 9(3)/9(4).
6. **Transport & E-Way Bill Details**: Fill Vehicle No., Transporter Name, LR/RR Date, and E-Way Bill Number if consignment > ₹50,000.
7. **Round-off**: Exact round-off to nearest rupee is computed automatically.
8. Click **"Save & Print" (Ctrl+S)**: Produces multi-tier ReportLab PDF with dynamic barcode and QR code.

### 4.3 Delivery Challans (F6)
Under **Rule 55 of CGST Rules, 2017**, move goods for:
- Job work / subcontracting
- Trade exhibitions and demonstrations
- Goods sent on approval basis  
*Note: In Settings, you can configure whether monetary values are displayed or suppressed on Delivery Challans.*

### 4.4 Sales Returns & Credit Notes (F8)
When goods are returned or invoice value reduced:
1. Open **Sales Returns (F8)** > Click **"+ New Return"**.
2. Select original invoice.
3. Select return quantity.
4. System automatically credits customer ledger, updates perpetual inventory balance, and generates compliant Section 34 Credit Note PDF.

---

## 5. Purchases & Supplier Accounting (F7)

1. Create Purchase Orders with expected delivery dates.
2. When vendor delivers shipment, click **"Receive Goods"**:
   - Stock quantities in product inventory update immediately.
   - Generates purchase voucher crediting vendor's ledger account.
   - Logs Input Tax Credit (ITC) for GSTR-3B Table 4.

---

## 6. Cash, Bank & Expense Management (F10)

- **Cash In / Customer Receipt**: Record customer remittances against outstanding invoices.
- **Cash Out / Supplier Payment**: Record disbursements to suppliers.
- **Contra Transfer**: Transfer funds between Cash-in-hand and Bank accounts without affecting P&L.
- **Expense Recording**: Log operating expenses (Rent, Electricity, Freight, Office Supplies) with expense categorization and tax treatment.

---

## 7. GST Statutory Returns & Government JSON Tool (F11)

### 7.1 GSTR-1 Outward Supplies
- Automatically categorizes outward sales into:
  - **B2B**: Supplies to registered taxable persons.
  - **B2CL**: Large inter-state supplies to unregistered persons (> ₹2,50,000).
  - **B2CS**: Intra-state and small inter-state supplies to unregistered persons.
  - **CDNR / CDNUR**: Credit/debit notes.
  - **HSN Summary**: Grouped by HSN code with quantities and tax values.
- Click **"Export GSTR-1 JSON"** to produce an official JSON file directly importable into the **Government GST Offline Tool (v1.3+)**.
- Click **"Export for CA (Excel)"** to generate a formatted multi-sheet Excel file for tax auditor review.

### 7.2 GSTR-3B Monthly Return Feeder
- Computes outward tax liability (Table 3.1) and eligible Input Tax Credit (Table 4) from purchases, calculating net tax payable.

---

## 8. Financial Statements & Reporting

- **Daybook (F9)**: Chronological register of every debit and credit transaction.
- **Profit & Loss**: Gross Profit (Sales - COGS) minus Operating Expenses = Net Profit.
- **Trial Balance**: Complete debit/credit ledger equality verification.

---

## 9. Data Protection, Backup & Disaster Recovery

### 9.1 Creating 1-Click Backups
Navigate to **Settings (F12)** > **💾 Backup & Database Management**:
- Click **"Backup Database Now"**: Creates a timestamped `.db` backup in `%APPDATA%\BillFlow\backups\`.
- Automatic rolling retention maintains the last **14 backups**, automatically pruning older archives.

### 9.2 Restoring from Backup
1. In Settings > Backup tab, select an existing backup from the history list or browse for a backup file.
2. Click **"Restore Selected Backup"**: System verifies backup file integrity and page headers before safely replacing the working database.

---
*End of User Guide.*

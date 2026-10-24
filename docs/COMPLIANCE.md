# BillFlow Suite: Indian GST & Statutory Compliance Documentation

**Document Version:** 1.0.0 (Production Release)  
**Applicability:** Financial Year 2024-25, 2025-26, 2026-27  
**Jurisdiction:** Central Goods and Services Tax Act, 2017 (CGST Act) & Respective SGST/UTGST/IGST Acts  
**Target Audience:** Chartered Accountants, Tax Auditors, Compliance Officers, System Administrators  

---

## 1. Executive Summary

BillFlow Suite is designed from the ground up to comply with Indian Goods and Services Tax (GST) statutes, rules, and prescribed reporting formats. This document sets out the regulatory framework, thresholds, statutory rules, data mapping, and audit checklists implemented in the application.

---

## 2. E-Invoicing Framework & Thresholds

### 2.1 Statutory Basis & Evolution
E-invoicing was introduced under **Rule 48(4) of the CGST Rules, 2017**. The phased rollout by the Central Board of Indirect Taxes and Customs (CBIC) has progressed through multiple notifications:
- **Phase I (Notification 13/2020-CT):** Turnover > ₹500 Cr (Oct 2020)
- **Phase II (Notification 88/2020-CT):** Turnover > ₹100 Cr (Jan 2021)
- **Phase III (Notification 05/2021-CT):** Turnover > ₹50 Cr (Apr 2021)
- **Phase IV (Notification 01/2022-CT):** Turnover > ₹20 Cr (Apr 2022)
- **Phase V (Notification 17/2022-CT):** Turnover > ₹10 Cr (Oct 2022)
- **Phase VI (Notification 10/2023-CT):** **Turnover > ₹5 Crores** (Mandatory w.e.f. August 1, 2023)

### 2.2 Mandatory Applicability Criteria
1. **Threshold Test:** Any registered person whose **Aggregate Annual Turnover (AATO)** across PAN exceeds **₹5 Crores** in any preceding financial year from 2017-18 onward.
2. **Transaction Types Covered:**
   - Business-to-Business (B2B) taxable supplies
   - Supplies to Special Economic Zones (SEZ Developer / SEZ Unit)
   - Export supplies (with or without payment of tax)
   - Deemed exports
   - Credit Notes and Debit Notes related to B2B supplies
3. **Exempted Entities (Rule 48(4)):**
   - Special Economic Zone (SEZ) Units (Developers are *not* exempt)
   - Insurers, Banking companies, Financial Institutions, NBFCs
   - Goods Transport Agencies (GTA)
   - Suppliers of passenger transportation services
   - Suppliers of services by way of admission to exhibition of cinematograph films in multiplex screens
   - Government Departments and Local Authorities

### 2.3 Invoice Registration Portal (IRP) Workflow
When e-invoicing is mandatory:
1. **JSON Payload Generation:** The billing software produces a JSON file following the **INV-01 standard schema** published by the GST Council.
2. **IRN Generation:** The IRP computes a 64-character hash using **SHA-256** based on:
   `Supplier GSTIN + Financial Year + Document Type + Document Number`
3. **Digital Signature & QR Code:** The IRP signs the invoice JSON with the government private key and generates a signed 2D QR code.
4. **Valid Tax Invoice:** An invoice without the IRN and signed QR code is legally deemed invalid under Rule 48(5) for entities crossing the threshold.

### 2.4 BillFlow Suite Compliance Posture & Status
- **Official Portal Turnover Threshold:** **₹5 Crores** aggregate annual turnover (w.e.f. 1 August 2023 per Notification 10/2023-CT).
- **Direct Real-Time IRP API Integration:** **NOT IMPLEMENTED** (BillFlow is an offline desktop system; it does NOT generate instantaneous NIC IRN hashes or signed QR codes via direct portal API).
- **Compliance Status:** **PARTIAL / NOT COMPLIANT for Enterprises > ₹5 Cr needing automated direct e-invoicing**. For eligible enterprises, BillFlow provides GSTR-1 offline JSON exports and CSV registers for batch upload via the Government Offline Tool or third-party GSP utilities.
- **Below ₹5 Cr Aggregate Turnover:** **COMPLIANT** per CGST Rule 46 (tax invoice with HSN, dual tax splits, reverse charge indicators, and statutory particulars).

---

## 3. E-Way Bill (EWB) Rules & Transportation Compliance

### 3.1 Statutory Basis (Rule 138 of CGST Rules, 2017)
An Electronic Way Bill (E-Way Bill) is mandatory for the movement of goods of consignment value exceeding prescribed limits.

### 3.2 Thresholds & Limits
- **Inter-State Movement:** Consignment value exceeding **₹50,000** (Mandatory across all States and Union Territories).
- **Intra-State Movement:** State-specific thresholds:
  - Default: ₹50,000
  - West Bengal: ₹1,00,000 (intra-state exempt up to ₹1,00,000 for non-sponge-iron items)
  - Maharashtra: ₹1,00,000
  - Delhi: ₹1,00,000
  - Tamil Nadu: ₹1,00,000
  - Bihar: ₹2,00,000 for specified goods
- **Mandatory EWB irrespective of value:**
  - Inter-state transfer of goods by principal to job-worker
  - Inter-state transfer of handicraft goods by exempt dealers

### 3.3 Structure of E-Way Bill
- **Part A (Form GST EWB-01):**
  - GSTIN of Supplier & Recipient
  - Place of Dispatch & Place of Delivery (6-digit Postal PIN Codes)
  - Invoice / Delivery Challan Number and Date
  - HSN Code (Minimum 2 or 4 digits depending on turnover)
  - Taxable Value and Tax Amounts (CGST, SGST, IGST, Cess)
  - Reason for Transportation (Supply, Export, Job Work, Sales Return, Line Sale, etc.)
- **Part B (Vehicle / Transporter Details):**
  - Transporter Document Number (GR / RR / Airway Bill / Bill of Lading)
  - Vehicle Registration Number

### 3.4 Validity Periods (Rule 138(10))
| Cargo Type | Distance Threshold | Validity Period |
| :--- | :--- | :--- |
| **Regular Cargo** | Up to 200 km | 1 Day |
| **Regular Cargo** | Every additional 200 km or part thereof | +1 Additional Day |
| **Over Dimensional Cargo (ODC) / Multimodal with Ship** | Up to 20 km | 1 Day |
| **Over Dimensional Cargo (ODC)** | Every additional 20 km or part thereof | +1 Additional Day |

### 3.5 Delivery Challan Compliance (Rule 55)
Under **Rule 55 of CGST Rules, 2017**, goods can be moved on a Delivery Challan instead of a tax invoice for:
1. Supply of liquid gas where quantity is not known at dispatch
2. Transportation of goods for job work
3. Transportation of goods for reasons other than supply (e.g., branch transfers, exhibitions, demo units)
4. Goods sent on approval basis

**BillFlow Implementation (Rule 55(1)):**
Per CGST Rule 55(1), every delivery challan requires taxable value. Where goods are transported for supply to the consignee (e.g. delivery with invoice to follow, line sale, approval), the challan displays taxable value, GST rate, and tax amounts. For non-supply movements (e.g. job work, intra-firm transfer, exhibitions), taxable value is shown while tax columns are omitted. Price-free printing is permitted strictly when legally exempt or explicitly flagged with statutory justification.

---

## 4. CGST Rule 46: 16 Mandatory Invoice Fields Checklist

Rule 46 of the CGST Rules, 2017 specifies 16 mandatory particulars that must be contained in a tax invoice. Below is the statutory verification matrix for BillFlow Suite:

| # | Statutory Requirement (Rule 46) | Field in BillFlow Database | UI / ReportLab PDF Location | Status |
| :-: | :--- | :--- | :--- | :-: |
| **1** | Name, address, and GSTIN of supplier | `CompanyProfile.name`, `address`, `gstin`, `state`, `state_code` | Header & "From" section on Page 1 | **COMPLIANT** |
| **2** | Consecutive serial number (<= 16 chars, alphanumeric, unique per FY) | `Invoice.invoice_number` (e.g., `INV/2026-27/0001`) | Invoice Title Box & Top Right | **COMPLIANT** |
| **3** | Date of invoice issue | `Invoice.invoice_date` (`datetime.date`) | Top Right Metadata Grid | **COMPLIANT** |
| **4** | Name, address, and GSTIN/UIN of recipient (if registered) | `Party.name`, `address`, `gstin`, `state`, `state_code` | "Billed To" Box | **COMPLIANT** |
| **5** | Name, address of recipient + delivery address + State code (if unregistered & value >= ₹50,000) | `Party.name`, `address`, `state_code`, `Invoice.shipping_address` | "Billed To" & "Shipped To" Boxes | **COMPLIANT** |
| **6** | HSN code of goods or SAC (Accounting Code of Services) | `InvoiceItem.hsn_code` / `Product.hsn_code` | Column 2 of Itemized Table & HSN Summary Table | **COMPLIANT** |
| **7** | Description of goods or services | `InvoiceItem.description` / `Product.name` | Column 1 of Itemized Table | **COMPLIANT** |
| **8** | Quantity in case of goods and unit or UQC | `InvoiceItem.quantity`, `Product.unit` (NOS, KGS, PCS, BOX, MTR, etc.) | Column 3 of Itemized Table | **COMPLIANT** |
| **9** | Total value of supply of goods or services | `Invoice.subtotal` (`Decimal`) | Subtotal row before discounts | **COMPLIANT** |
| **10** | Taxable value of supply taking into account discount or abatement | `Invoice.taxable_amount` (`Decimal`) | Taxable Value Column & Summary Box | **COMPLIANT** |
| **11** | Rate of tax (CGST, SGST, IGST, Cess) | `InvoiceItem.gst_rate` (0%, 5%, 12%, 18%, 28%) | Tax Column & HSN Breakup Table | **COMPLIANT** |
| **12** | Amount of tax charged (CGST, SGST, IGST, Cess separately) | `Invoice.cgst_amount`, `Invoice.sgst_amount`, `Invoice.igst_amount` | Summary Breakdown & HSN Breakup Grid | **COMPLIANT** |
| **13** | Place of supply along with the name of State (inter-State supply) | `Party.state` & `Party.state_code` / `Invoice.pos_state_code` | "Place of Supply: [State] ([Code])" in Header | **COMPLIANT** |
| **14** | Address of delivery where different from place of supply | `Invoice.shipping_address` | Distinct "Shipped To / Consignee" Box | **COMPLIANT** |
| **15** | Whether tax is payable on reverse charge basis (RCM) | `Invoice.reverse_charge` (`Boolean`: Yes / No) | Explicit "Tax Payable on Reverse Charge: YES/NO" Tag | **COMPLIANT** |
| **16** | Signature or digital signature of supplier or authorized representative | Company stamp/signature block | Footer Canvas: "For [Company Name]\nAuthorized Signatory" | **COMPLIANT** |

---

## 5. Section 34 of CGST Act: Credit & Debit Note Statutory Guidelines

### 5.1 Grounds for Issuance
Under **Section 34(1)** (Credit Notes) and **Section 34(3)** (Debit Notes):
1. **Credit Note (CN):**
   - Taxable value or tax charged in invoice exceeds actual value or tax payable.
   - Goods supplied are returned by recipient.
   - Goods or services supplied are found to be deficient.
2. **Debit Note (DN):**
   - Taxable value or tax charged in invoice is found to be less than actual value or tax payable.

### 5.2 Statutory Time Limits (Finance Act 2022 Amendment)
A registered person who issues a credit note in relation to a supply of goods or services must declare the details of such credit note in the return for the month during which such credit note has been issued, but **not later than**:
- **30th day of November** following the end of the financial year in which such supply was made, OR
- The date of furnishing of the relevant **Annual Return (GSTR-9)**,  
*whichever is earlier*.

### 5.3 Mandatory Linking & Accounting Requirements
- Every Credit Note and Debit Note must reference the **original tax invoice number** and **date**.
- If multiple invoices are adjusted, each invoice mapping must be preserved in the audit log (`app/services/audit_service.py`).
- **No Reduction in Output Tax:** Under Section 34(2) proviso, no reduction in output tax liability is permitted to the supplier if the incidence of tax and interest on such supply has been passed on to any other person.

---

## 6. GSTR-1 & GSTR-3B Classification Rules

### 6.1 GSTR-1 Outward Supply Categorization
BillFlow automatically classifies outward transactions into official GST Portal tables (`app/services/gst_report_service.py`):
1. **Table 4 (B2B):** Invoices issued to recipients with valid 15-character GSTINs.
2. **Table 5 (B2CL):** Inter-state invoices issued to unregistered customers where invoice value exceeds:
   - **₹1,00,000** for supplies on or after **1 August 2024** (Notification No. 12/2024 – Central Tax).
   - **₹2,50,000** for supplies prior to **1 August 2024**.
3. **Table 7 (B2CS):** All intra-state supplies to unregistered customers, and inter-state supplies to unregistered customers where invoice value is at or below the applicable statutory B2CL threshold (₹1 Lakh w.e.f. 01-Aug-2024, ₹2.5 Lakh prior).
4. **Table 9B (CDNR):** Credit/Debit notes issued to registered parties with linked invoice numbers.
5. **Table 9B (CDNUR):** Credit/Debit notes issued to unregistered parties for inter-state transactions exceeding the applicable B2CL threshold.
6. **Table 12 (HSN Summary):** Quantity, UQC, total value, taxable value, and tax breakdown grouped by HSN code.

### 6.2 GSTR-3B Monthly Return Feeder
1. **Table 3.1(a):** Outward taxable supplies (other than zero rated, nil rated and exempted).
2. **Table 4(A)(5):** All other Input Tax Credit (ITC) from inward supplier invoices and registered purchase vouchers.
3. **Table 4(B):** Ineligible or reversed ITC under Rule 38, 42, and 43.
4. **Table 5.1:** Interest and late fee payable.

---

## 7. Chartered Accountant (CA) Pre-Audit & Sign-Off Questionnaire

This 25-point verification questionnaire is designed for CAs and Tax Auditors before signing off on books, GSTR-9 annual returns, and GSTR-9C reconciliation statements:

### A. Books vs. GST Portal Reconciliation
- [ ] **Q01:** Does the Total Turnover in the Audited P&L match the aggregate value of supplies declared in GSTR-1 (Tables 4, 5, 7, 8, 11)?
- [ ] **Q02:** Are there any unbilled deliveries under Rule 55 Delivery Challans older than 6 months (job work) or 1 year (capital goods) that must be treated as deemed supplies?
- [ ] **Q03:** Have all Credit Notes issued during the FY been accounted for on or before the 30th November deadline?
- [ ] **Q04:** Does Output Tax Liability in the General Ledger (CGST, SGST, IGST Output accounts) match the cumulative liability paid in cash and ITC via GSTR-3B Table 6.1?
- [ ] **Q05:** Have rounding-off differences been booked to an Expense/Income account (e.g., "Round-off Account") rather than distorting statutory tax amounts?

### B. Input Tax Credit (ITC) Verification (Section 16 & 17)
- [ ] **Q06:** Are all inward supplies supported by valid tax invoices, debit notes, or bill of entry in possession of the taxpayer (Sec 16(2)(a))?
- [ ] **Q07:** Has ITC been claimed only for goods/services actually received (Sec 16(2)(b))?
- [ ] **Q08:** Have all suppliers been paid within 180 days from the invoice date (second proviso to Sec 16(2))? If not, has proportionate ITC been reversed with interest?
- [ ] **Q09:** Have blocked credits under Section 17(5) (motor vehicles, food/catering, health insurance, club memberships, goods lost/stolen/destroyed) been excluded from ITC claims?
- [ ] **Q10:** Has common ITC been apportioned between business and non-business/exempt supplies per Rules 42 and 43?

### C. HSN Classification & Rate Validation
- [ ] **Q11:** Does the entity meet the 4-digit HSN requirement (AATO up to ₹5 Cr) or 6-digit HSN requirement (AATO above ₹5 Cr) on all B2B invoices?
- [ ] **Q12:** Are HSN codes mapped correctly to statutory GST rate slabs (0%, 5%, 12%, 18%, 28%) with zero rate mismatches?
- [ ] **Q13:** Are mixed supplies and composite supplies correctly identified and taxed at the principal supply rate or highest rate?

### D. Reverse Charge Mechanism (RCM - Sec 9(3) & 9(4))
- [ ] **Q14:** Has RCM tax been paid in cash on notified services: Goods Transport Agency (GTA), legal services by advocates, sponsorship services, director remuneration?
- [ ] **Q15:** Has eligible ITC on RCM payments been claimed in the same month after cash payment?
- [ ] **Q16:** Have payment vouchers been issued to unregistered suppliers under Section 31(3)(g)?

### E. Financial Integrity & Period Locking
- [ ] **Q17:** Has `scripts/verify_books.py` been executed on the production database with all 7 integrity checks passing (Exit Code 0)?
- [ ] **Q18:** Is the Trial Balance completely balanced (Total Debits == Total Credits with difference == 0.00)?
- [ ] **Q19:** Is there any negative cash balance on any date throughout the financial year?
- [ ] **Q20:** Have period locks (`PeriodLock` model) been activated for all closed quarters and filed months to prevent retroactive edits?
- [ ] **Q21:** Does the immutable audit log (`AuditLog` table) record all cancellations, deletions, and back-dated entries with timestamp and user attribution?
- [ ] **Q22:** Have physical stock counts been reconciled with perpetual book stock, and valuation verified on Cost or Net Realizable Value (NRV) basis (AS-2 / Ind AS-2)?
- [ ] **Q23:** Have inter-state supplies to unregistered persons exceeding the statutory threshold (₹1 Lakh post 01-Aug-2024; ₹2.5 Lakh prior) been correctly categorized under Table 5 (B2CL) with Place of Supply?
- [ ] **Q24:** Are all foreign currency export invoices converted using CBIC notified exchange rates on the date of invoice?
- [ ] **Q25:** Has the rolling backup retention (minimum 14 backups) and database WAL integrity check been verified before annual closing?

---

## 8. Compliance Sign-Off Template

```text
================================================================================
                    STATUTORY GST AUDIT & SIGN-OFF CERTIFICATE
================================================================================
Client Legal Name: _____________________________________________________________
Trade Name:        _____________________________________________________________
GSTIN:             _____________________________________________________________
Financial Year:    ______________________   Assessment Year: ___________________

I/We have examined the books of account, registers, invoices, and statutory returns
generated by BillFlow Suite for the period from ____________ to ____________.

Subject to the notes and observations annexed hereto:
1. The accounting books and registers satisfy the requirements of Section 35 of the
   CGST Act, 2017 and Rule 56 of the CGST Rules, 2017.
2. Invoices issued conform to the 16 mandatory particulars of CGST Rule 46.
3. Credit and Debit Notes comply with the provisions and timelines of Section 34.
4. Input Tax Credit claimed in GSTR-3B is reconciled with eligible inward supplies.
5. The digital books pass all automated mathematical and referential integrity checks.

Name of Chartered Accountant: __________________________________________________
Membership Number:            __________________________________________________
Firm Registration Number:     __________________________________________________
UDIN:                         __________________________________________________
Date:                         ______________________
Place:                        ______________________
================================================================================
```

---
*End of Compliance Document.*

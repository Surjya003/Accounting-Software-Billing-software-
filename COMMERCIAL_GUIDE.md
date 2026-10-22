# VyaparLedger Pro — Commercial Pricing, Licensing & Support Playbook

Comprehensive vendor guide for selling, licensing, onboarding, and supporting **VyaparLedger Pro** with Indian B2B traders, distributors, and wholesalers.

---

## 1. Commercial Pricing & Business Model

Recommended pricing structures tailored for Indian SME / B2B traders:

### 💰 Plan A: Lifetime License + Optional AMC (Recommended)
*Best for Indian traders who prefer outright software ownership.*

| Component | Price (INR) | Details |
| :--- | :---: | :--- |
| **One-Time License Fee** | **₹7,999** | Single-PC perpetual offline license key. Lifetime usage with zero mandatory recurring fees. |
| **Onboarding & Training** | **FREE** | 1-hour remote AnyDesk walkthrough & initial party master import. |
| **Annual Maintenance Contract (AMC)** *(Optional after Year 1)* | **₹2,499 / year** | Priority WhatsApp/Phone support, tax rate / GST format updates, database maintenance, free license transfer on PC change. |

---

### 💳 Plan B: Annual Subscription (SaaS on Desktop)
*Best for price-sensitive new businesses.*

| Component | Price (INR) | Details |
| :--- | :---: | :--- |
| **Annual Subscription** | **₹3,999 / year** | 1-Year license key. Includes all feature updates, version upgrades, and unlimited WhatsApp support. |
| **Multi-PC Addon (Per Extra PC)** | **₹1,999 / year** | Additional machine license key for accountant / billing terminal. |

---

## 2. Hardware-Locked License Key Issuance Workflow

Every customer PC generates a unique **16-character Machine ID** (e.g. `VYAP-A1B2-C3D4-E5F6`). The vendor generates a signed offline key using the built-in CLI tool.

### 🔑 Step-by-Step Vendor Keygen:

1. **Ask the client for their Machine ID & Registered Business Name**:
   - The client can see their Machine ID in **Settings → License & Activation** (or on the trial expiry screen) and click **"Copy Machine ID"**.

2. **Generate Key using the Vendor Keygen Tool**:
   Open terminal on your vendor computer:
   ```bash
   # For Lifetime Perpetual License:
   python tools/keygen.py --machine "VYAP-A1B2-C3D4-E5F6" --company "Sita Ram & Sons Traders"

   # For 1-Year Annual License (e.g., expiring 31-Dec-2026):
   python tools/keygen.py --machine "VYAP-A1B2-C3D4-E5F6" --company "Sita Ram & Sons Traders" --expiry "2026-12-31"
   ```

3. **Deliver Key to Customer via WhatsApp / Email**:
   - Send the generated key (e.g. `P-4B92-7E1A-88D1-9F2B` or `261231-89AC-4412-BB90-112A`).
   - Customer pastes it into **Settings → License & Activation** and clicks **"⚡ Activate Commercial License"**.
   - The application instantly activates without requiring an internet connection.

---

## 3. Customer Onboarding & Clean PC Deployment

### 📦 Clean PC Deployment in 3 Easy Steps (No Python Required):

1. **Deliver the Standalone Executable**:
   - Copy `dist/VyaparLedger.exe` to a USB drive or Google Drive download link.
2. **Place in Client Application Directory**:
   - Recommend creating a folder `C:\VyaparLedger\` and placing `VyaparLedger.exe` inside it.
   - Create a Desktop Shortcut for easy access.
3. **First-Time Launch**:
   - Double-click `VyaparLedger.exe`.
   - SQLite database, tables, and settings auto-initialize in `<AppFolder>\data\accounting.db`.
   - Go to **Settings & Maintenance → Company Profile** to configure their business name, address, GSTIN, and company logo.

---

## 4. Customer Support SLA & Contact Matrix

Provide this SLA card to your customer upon purchase:

### 📞 Support Channels
- **WhatsApp Support Desk**: `+91 XXXXX XXXXX` *(10:00 AM – 7:00 PM IST, Monday to Saturday)*
- **Email Support**: `support@yourdomain.com` *(Response within 4 business hours)*
- **Remote Desktop Assistance**: AnyDesk / TeamViewer support for database backup restoration or initial data import.

### 🛡️ Bug Triage & Resolution SLA
- **Critical (App cannot open or DB lock)**: Resolved within **2 hours**.
- **High (Voucher calculation / Print format issue)**: Resolved within **6 hours**.
- **Normal (Feature request / minor UI tweak)**: Included in the next minor version update.

---

## 5. Client Data Safety & Backup Protocol

Advise the customer to follow this simple rule:

1. **Daily Backup (Before Closing Shop)**:
   - Go to **Settings & Backup → Database Backup & Maintenance**.
   - Click **"📦 Create Instant Backup Now"** and save to an external USB flash drive or Cloud Drive (Google Drive / OneDrive / Dropbox).
2. **Disaster Recovery**:
   - If their computer crashes or gets infected, install `VyaparLedger.exe` on their new computer.
   - Click **"🔄 Restore Database from Backup File"** and select their latest `.db` backup file.
   - All party ledgers, historical invoices, and GST records will restore instantly.

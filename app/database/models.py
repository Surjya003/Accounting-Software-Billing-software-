"""
SQLAlchemy Database Models for VyaparLedger Pro
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, Date, DateTime,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CompanyProfile(Base):
    __tablename__ = "company_profile"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, default="My Trading Company")
    trade_name = Column(String(200), nullable=True)
    gstin = Column(String(15), nullable=True)
    pan = Column(String(10), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True, default="Maharashtra")
    state_code = Column(String(2), nullable=True, default="27")
    pincode = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    website = Column(String(100), nullable=True)
    
    # Banking details
    bank_name = Column(String(100), nullable=True)
    bank_account_no = Column(String(50), nullable=True)
    bank_ifsc = Column(String(20), nullable=True)
    bank_branch = Column(String(100), nullable=True)
    upi_id = Column(String(100), nullable=True)
    logo_path = Column(String(500), nullable=True)
    
    terms_conditions = Column(Text, nullable=True, default="1. Goods once sold will not be taken back.\n2. Interest @ 18% p.a. will be charged if payment is delayed beyond due date.\n3. Subject to local jurisdiction.")
    financial_year = Column(String(10), nullable=True, default="2024-25")
    allow_negative_stock = Column(Boolean, default=False, nullable=False)

    # PDF Document Suite Settings
    declaration = Column(Text, nullable=True, default="We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.")
    terms_quotation = Column(Text, nullable=True, default="1. Validity: 30 days from date of quotation.\n2. Payment: 100% against delivery.\n3. Taxes: GST extra as applicable.")
    terms_po = Column(Text, nullable=True, default="1. Quote PO number on all invoices and delivery challans.\n2. Goods subject to inspection and approval.")
    notes_challan = Column(Text, nullable=True, default="Goods sent on approval/job work basis. Not for sale.")
    terms_proforma = Column(Text, nullable=True, default="Goods will be dispatched immediately upon receipt of full payment.")
    seal_path = Column(String(500), nullable=True)
    signature_path = Column(String(500), nullable=True)
    number_format = Column(String(20), nullable=True, default="Indian")
    show_value_on_challan = Column(Boolean, default=False)
    print_all_copies = Column(Boolean, default=False)
    print_hsn_summary = Column(Boolean, default=True)
    adaptive_item_font_enabled = Column(Boolean, default=True, nullable=False)
    adaptive_item_font_max = Column(Numeric(4, 2), default=13.0, nullable=False)
    adaptive_item_font_min = Column(Numeric(4, 2), default=7.5, nullable=False)
    stock_valuation_method = Column(String(50), nullable=True, default="weighted_average")
    ageing_allocation_method = Column(String(50), nullable=True, default="Oldest first")
    whatsapp_template = Column(Text, nullable=True, default="Dear {party_name},\n\nGreetings from *{company_name}*!\n\nThis is a gentle reminder that your current outstanding balance is *₹{amount}*.\n\n📊 *Overdue Aging Summary:*\n• 0-30 Days: ₹{b0}\n• 31-60 Days: ₹{b31}\n• 61-90 Days: ₹{b61}\n• 90+ Days: ₹{b90}\n\n💳 *Bank Transfer Details:*\n{bank_details}\n\nKindly arrange for payment at your earliest convenience. If already paid, please ignore this message.\n\nWarm regards,\n*{company_name}*")

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Party(Base):
    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    party_type = Column(String(20), nullable=False, default="Customer")  # Customer, Supplier, Both
    gstin = Column(String(15), nullable=True, index=True)
    pan = Column(String(10), nullable=True)
    contact_person = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True, index=True)
    email = Column(String(100), nullable=True)
    
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True, default="Maharashtra")
    state_code = Column(String(2), nullable=True, default="27")
    pincode = Column(String(10), nullable=True)

    # Separate Shipping Address
    shipping_address = Column(Text, nullable=True)
    shipping_city = Column(String(100), nullable=True)
    shipping_state = Column(String(100), nullable=True)
    shipping_state_code = Column(String(2), nullable=True)
    shipping_pincode = Column(String(10), nullable=True)
    same_as_billing = Column(Boolean, default=True)
    
    credit_period_days = Column(Integer, default=30)
    credit_limit = Column(Numeric(15, 2), default=Decimal("0.00"))
    
    # Opening Balance at start of bookkeeping
    opening_balance = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    opening_balance_type = Column(String(2), default="Dr", nullable=False)  # Dr (Receivable) or Cr (Payable)
    opening_balance_date = Column(Date, nullable=True, default=date.today)
    
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    vouchers = relationship("Voucher", back_populates="party", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_party_name_type", "name", "party_type"),
    )

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        d['opening_balance'] = float(self.opening_balance) if self.opening_balance is not None else 0.0
        d['credit_limit'] = float(self.credit_limit) if self.credit_limit is not None else 0.0
        return d


class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    voucher_number = Column(String(50), unique=True, nullable=False, index=True)
    voucher_type = Column(String(20), nullable=False, index=True)  # Debit, Credit, Journal
    voucher_date = Column(Date, nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Product / item description for Debit and Credit vouchers
    product = Column(String(255), nullable=True)  # e.g. "ACS560 Drive x2"
    
    # External reference (e.g. Supplier Bill No, Buyer PO No, Cheque/UTR No)
    reference_no = Column(String(100), nullable=True, index=True)
    reference_date = Column(Date, nullable=True)
    
    payment_mode = Column(String(50), nullable=True)  # Cash, Bank Transfer, UPI, Cheque, Other
    
    # Financial breakdowns
    amount_untaxed = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    cgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_tax = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    
    # Explicit debit/credit for Journal entries or direct adjustments
    # For Sale: Dr Party = total_amount
    # For Purchase: Cr Party = total_amount
    # For Receipt: Cr Party = total_amount (money in from customer)
    # For Payment: Dr Party = total_amount (money out to supplier)
    # For Journal: specified explicitly
    debit_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    credit_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    
    narration = Column(Text, nullable=True)
    is_tax_invoice = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    party = relationship("Party", back_populates="vouchers")
    items = relationship("VoucherItem", back_populates="voucher", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_voucher_date_type", "voucher_date", "voucher_type"),
        Index("idx_voucher_party_date", "party_id", "voucher_date"),
    )

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['amount_untaxed', 'cgst_amount', 'sgst_amount', 'igst_amount', 'total_tax', 'total_amount', 'debit_amount', 'credit_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['party_name'] = self.party.name if self.party else ""
        return d

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)


class VoucherItem(Base):
    __tablename__ = "voucher_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    item_description = Column(String(255), nullable=False)
    hsn_sac_code = Column(String(20), nullable=True)
    quantity = Column(Numeric(12, 3), default=Decimal("1.000"), nullable=False)
    unit = Column(String(20), default="PCS", nullable=False)  # PCS, KGS, BOX, MTR, NOS, etc.
    unit_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    discount_pct = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    
    taxable_value = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    gst_rate_pct = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    cgst_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    cgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    sgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    igst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_item_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    voucher = relationship("Voucher", back_populates="items")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['quantity', 'unit_price', 'discount_pct', 'taxable_value', 'gst_rate_pct', 'cgst_rate', 'cgst_amount', 'sgst_rate', 'sgst_amount', 'igst_rate', 'igst_amount', 'total_item_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        return d


class LicenseRecord(Base):
    __tablename__ = "license_record"

    id = Column(Integer, primary_key=True)
    machine_fingerprint = Column(String(100), nullable=False)
    license_key = Column(String(255), nullable=True)
    issued_to = Column(String(200), nullable=True)
    activation_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    is_perpetual = Column(Boolean, default=False)
    status = Column(String(20), default="TRIAL")  # TRIAL, ACTIVE, EXPIRED, REVOKED
    trial_start_date = Column(Date, default=date.today)
    last_verified_at = Column(DateTime, default=datetime.now)


# =============================================================================
# BILLING MODULE MODELS
# =============================================================================

class Product(Base):
    """Product / Inventory item used in invoices, POs, and challans."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    hsn_code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    unit = Column(String(20), default="PCS", nullable=False)
    price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)          # Selling Price (Retail)
    purchase_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=True)  # Buying Price
    wholesale_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=True)
    tax_rate = Column(Numeric(5, 2), default=Decimal("18.00"), nullable=False)       # GST %: 5, 12, 18, 28
    stock_quantity = Column(Numeric(12, 3), default=Decimal("0.000"), nullable=False)
    low_stock_threshold = Column(Numeric(12, 3), default=Decimal("10.000"), nullable=False)
    barcode = Column(String(100), unique=True, nullable=True)
    category = Column(String(100), nullable=True)
    image_path = Column(String(500), nullable=True)
    supplier_id = Column(Integer, ForeignKey("parties.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    supplier = relationship("Party", foreign_keys=[supplier_id])
    invoice_items = relationship("InvoiceItem", back_populates="product")

    __table_args__ = (
        Index("idx_product_name_cat", "name", "category"),
    )

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['price', 'purchase_price', 'wholesale_price', 'tax_rate', 'stock_quantity', 'low_stock_threshold']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        return d


class Invoice(Base):
    """GST Tax Invoice header."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_date = Column(Date, nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    subtotal = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    cgst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    status = Column(String(20), default="draft", nullable=False, index=True)  # draft, final, cancelled
    notes = Column(Text, nullable=True)
    is_interstate = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Additional Features
    shipping_address = Column(Text, nullable=True)
    transporter_name = Column(String(200), nullable=True)
    vehicle_no = Column(String(50), nullable=True)
    lr_no = Column(String(50), nullable=True)
    lr_date = Column(Date, nullable=True)
    eway_bill_no = Column(String(50), nullable=True)
    destination = Column(String(100), nullable=True)
    terms_and_conditions = Column(Text, nullable=True)
    bank_name = Column(String(200), nullable=True)
    bank_ac_no = Column(String(50), nullable=True)
    bank_ifsc = Column(String(20), nullable=True)
    po_number = Column(String(50), nullable=True)   # Purchase Order reference
    pi_number = Column(String(50), nullable=True)   # Proforma Invoice reference

    # PDF Reference Grid & Details
    delivery_note = Column(String(100), nullable=True)
    mode_terms_of_payment = Column(String(100), nullable=True)
    reference_no_date = Column(String(100), nullable=True)
    other_references = Column(String(100), nullable=True)
    buyers_order_no = Column(String(100), nullable=True)
    buyers_order_date = Column(Date, nullable=True)
    dispatch_doc_no = Column(String(100), nullable=True)
    dispatched_through = Column(String(100), nullable=True)
    terms_of_delivery = Column(Text, nullable=True)
    place_of_supply = Column(String(100), nullable=True)
    reverse_charge = Column(Boolean, default=False)
    copy_label = Column(String(50), default="ORIGINAL FOR RECIPIENT")

    # Relationships
    party = relationship("Party", foreign_keys=[party_id])
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_invoice_date_status", "invoice_date", "status"),
    )

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['subtotal', 'cgst_total', 'sgst_total', 'igst_total', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['party_name'] = self.party.name if self.party else ""
        return d

    def __getitem__(self, item):
        alias_map = {
            "cgst_amount": "cgst_total",
            "sgst_amount": "sgst_total",
            "igst_amount": "igst_total",
        }
        attr = alias_map.get(item, item)
        if hasattr(self, attr):
            return getattr(self, attr)
        raise KeyError(item)

    @property
    def cgst_amount(self):
        return self.cgst_total

    @property
    def sgst_amount(self):
        return self.sgst_total

    @property
    def igst_amount(self):
        return self.igst_total


class InvoiceItem(Base):
    """Line item in an invoice."""
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    item_description = Column(String(255), nullable=False)
    hsn_code = Column(String(20), nullable=True)
    quantity = Column(Numeric(12, 3), default=Decimal("1.000"), nullable=False)
    unit = Column(String(20), default="PCS", nullable=False)
    unit_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    discount_pct = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    taxable_value = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    gst_rate_pct = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    cgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product", back_populates="invoice_items")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['quantity', 'unit_price', 'discount_pct', 'taxable_value', 'gst_rate_pct',
                   'cgst_amount', 'sgst_amount', 'igst_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['product_name'] = self.product.name if self.product else ""
        return d


class ProformaInvoice(Base):
    """Proforma Invoice (quotation) header."""
    __tablename__ = "proforma_invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proforma_number = Column(String(50), unique=True, nullable=False, index=True)
    proforma_date = Column(Date, nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    subtotal = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    cgst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    status = Column(String(20), default="draft", nullable=False)  # draft, sent, converted, expired
    notes = Column(Text, nullable=True)
    is_interstate = Column(Boolean, default=False)

    # Additional Features (same as Invoice)
    shipping_address = Column(Text, nullable=True)
    transporter_name = Column(String(200), nullable=True)
    vehicle_no = Column(String(50), nullable=True)
    lr_no = Column(String(50), nullable=True)
    lr_date = Column(Date, nullable=True)
    eway_bill_no = Column(String(50), nullable=True)
    destination = Column(String(100), nullable=True)
    terms_and_conditions = Column(Text, nullable=True)
    bank_name = Column(String(200), nullable=True)
    bank_ac_no = Column(String(50), nullable=True)
    bank_ifsc = Column(String(20), nullable=True)
    po_number = Column(String(50), nullable=True)
    pi_number = Column(String(50), nullable=True)

    valid_until = Column(Date, nullable=True)
    advance_percent = Column(Numeric(5, 2), default=Decimal("0.00"))
    advance_received = Column(Numeric(15, 2), default=Decimal("0.00"))
    payment_terms = Column(String(200), nullable=True)
    delivery_period = Column(String(100), nullable=True)
    customer_po_no = Column(String(100), nullable=True)
    customer_po_date = Column(Date, nullable=True)
    linked_invoice_reference = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    party = relationship("Party", foreign_keys=[party_id])
    items = relationship("ProformaItem", back_populates="proforma", cascade="all, delete-orphan")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['subtotal', 'cgst_total', 'sgst_total', 'igst_total', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['party_name'] = self.party.name if self.party else ""
        return d


class ProformaItem(Base):
    """Line item in a proforma invoice."""
    __tablename__ = "proforma_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proforma_id = Column(Integer, ForeignKey("proforma_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    item_description = Column(String(255), nullable=False)
    hsn_code = Column(String(20), nullable=True)
    quantity = Column(Numeric(12, 3), default=Decimal("1.000"), nullable=False)
    unit = Column(String(20), default="PCS", nullable=False)
    unit_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    discount_pct = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    taxable_value = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    gst_rate_pct = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    cgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    proforma = relationship("ProformaInvoice", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['quantity', 'unit_price', 'discount_pct', 'taxable_value', 'gst_rate_pct',
                   'cgst_amount', 'sgst_amount', 'igst_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        return d


class Quotation(Base):
    """Quotation / Estimate header — a formal price proposal to a customer."""
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quotation_number = Column(String(50), unique=True, nullable=False, index=True)
    quotation_date = Column(Date, nullable=False, index=True)
    valid_until = Column(Date, nullable=True)  # Quotation validity date
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    subtotal = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    cgst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    status = Column(String(20), default="draft", nullable=False)  # draft, sent, accepted, rejected, expired, converted
    notes = Column(Text, nullable=True)
    is_interstate = Column(Boolean, default=False)

    # Additional Features (same as Invoice/Proforma)
    shipping_address = Column(Text, nullable=True)
    transporter_name = Column(String(200), nullable=True)
    vehicle_no = Column(String(50), nullable=True)
    lr_no = Column(String(50), nullable=True)
    lr_date = Column(Date, nullable=True)
    eway_bill_no = Column(String(50), nullable=True)
    destination = Column(String(100), nullable=True)
    terms_and_conditions = Column(Text, nullable=True)
    bank_name = Column(String(200), nullable=True)
    bank_ac_no = Column(String(50), nullable=True)
    bank_ifsc = Column(String(20), nullable=True)
    po_number = Column(String(50), nullable=True)
    reference_number = Column(String(50), nullable=True)  # Customer's reference

    kind_attn = Column(String(100), nullable=True)
    enquiry_ref_date = Column(String(100), nullable=True)
    subject = Column(String(255), nullable=True)
    price_basis = Column(String(100), nullable=True)
    terms_payment = Column(String(200), nullable=True)
    terms_delivery = Column(String(200), nullable=True)
    terms_validity = Column(String(200), nullable=True)
    terms_freight = Column(String(200), nullable=True)
    terms_packing = Column(String(200), nullable=True)
    terms_warranty = Column(String(200), nullable=True)
    terms_taxes = Column(String(200), nullable=True)
    terms_inspection = Column(String(200), nullable=True)
    terms_jurisdiction = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    party = relationship("Party", foreign_keys=[party_id])
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_quotation_date_status", "quotation_date", "status"),
    )

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['subtotal', 'cgst_total', 'sgst_total', 'igst_total', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['party_name'] = self.party.name if self.party else ""
        return d


class QuotationItem(Base):
    """Line item in a quotation."""
    __tablename__ = "quotation_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    item_description = Column(String(255), nullable=False)
    hsn_code = Column(String(20), nullable=True)
    quantity = Column(Numeric(12, 3), default=Decimal("1.000"), nullable=False)
    unit = Column(String(20), default="PCS", nullable=False)
    unit_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    discount_pct = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    taxable_value = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    gst_rate_pct = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    cgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    quotation = relationship("Quotation", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['quantity', 'unit_price', 'discount_pct', 'taxable_value', 'gst_rate_pct',
                   'cgst_amount', 'sgst_amount', 'igst_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        return d


class PurchaseOrder(Base):
    """Purchase Order header."""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_number = Column(String(50), unique=True, nullable=False, index=True)
    po_date = Column(Date, nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    subtotal = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    status = Column(String(20), default="draft", nullable=False)  # draft, sent, received, cancelled
    notes = Column(Text, nullable=True)

    revision = Column(String(20), default="0")
    quotation_ref = Column(String(100), nullable=True)
    quotation_date = Column(Date, nullable=True)
    delivery_required_by = Column(Date, nullable=True)
    payment_terms = Column(String(200), nullable=True)
    delivery_terms = Column(String(100), nullable=True)
    mode_of_dispatch = Column(String(100), nullable=True)
    insurance = Column(String(100), nullable=True)
    ship_to_address = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    party = relationship("Party", foreign_keys=[party_id])
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['subtotal', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['party_name'] = self.party.name if self.party else ""
        return d


class PurchaseOrderItem(Base):
    """Line item in a purchase order."""
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    item_description = Column(String(255), nullable=False)
    hsn_code = Column(String(20), nullable=True)
    quantity = Column(Numeric(12, 3), default=Decimal("1.000"), nullable=False)
    received_quantity = Column(Numeric(12, 3), default=Decimal("0.000"), nullable=False)
    unit = Column(String(20), default="PCS", nullable=False)
    unit_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    delivery_date = Column(Date, nullable=True)
    item_code = Column(String(50), nullable=True)
    tax_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['quantity', 'unit_price', 'tax_rate', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        return d


class DeliveryChallan(Base):
    """Delivery Challan header."""
    __tablename__ = "delivery_challans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    challan_number = Column(String(50), unique=True, nullable=False, index=True)
    challan_date = Column(Date, nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    subtotal = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    cgst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_total = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    status = Column(String(20), default="sent", nullable=False)  # sent, received, returned, converted
    is_interstate = Column(Boolean, default=False)
    transport_details = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    reason_for_transportation = Column(String(50), default="Delivery (invoice to follow)")
    dispatch_datetime = Column(String(50), nullable=True)
    transporter_name = Column(String(200), nullable=True)
    transporter_id = Column(String(50), nullable=True)
    vehicle_no = Column(String(50), nullable=True)
    driver_name = Column(String(100), nullable=True)
    driver_mobile = Column(String(20), nullable=True)
    lr_no = Column(String(50), nullable=True)
    lr_date = Column(Date, nullable=True)
    eway_bill_no = Column(String(50), nullable=True)
    from_place = Column(String(100), nullable=True)
    to_place = Column(String(100), nullable=True)
    distance_km = Column(Numeric(10, 2), nullable=True)
    packages = Column(Integer, nullable=True)
    weight = Column(Numeric(10, 3), nullable=True)
    show_value = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    party = relationship("Party", foreign_keys=[party_id])
    items = relationship("ChallanItem", back_populates="challan", cascade="all, delete-orphan")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['subtotal', 'cgst_total', 'sgst_total', 'igst_total', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['party_name'] = self.party.name if self.party else ""
        return d


class ChallanItem(Base):
    """Line item in a delivery challan."""
    __tablename__ = "challan_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    challan_id = Column(Integer, ForeignKey("delivery_challans.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    item_description = Column(String(255), nullable=False)
    hsn_code = Column(String(20), nullable=True)
    quantity = Column(Numeric(12, 3), default=Decimal("1.000"), nullable=False)
    unit = Column(String(20), default="PCS", nullable=False)
    unit_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    qty_ordered = Column(Numeric(12, 3), nullable=True)
    remarks = Column(String(255), nullable=True)
    tax_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    cgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    igst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    challan = relationship("DeliveryChallan", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['quantity', 'unit_price', 'tax_rate', 'cgst_amount', 'sgst_amount', 'igst_amount', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        return d


class SalesReturn(Base):
    """Sales Return (Credit Note) header."""
    __tablename__ = "sales_returns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    return_number = Column(String(50), unique=True, nullable=False, index=True)
    return_date = Column(Date, nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    subtotal = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected

    reason_category = Column(String(50), default="Sales Return")
    original_invoice_no = Column(String(50), nullable=True)
    original_invoice_date = Column(Date, nullable=True)
    adjustment_mode = Column(String(50), default="Credit Note")
    adjustment_ref = Column(String(100), nullable=True)
    returned_via = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    party = relationship("Party", foreign_keys=[party_id])
    invoice = relationship("Invoice", foreign_keys=[invoice_id])
    items = relationship("SalesReturnItem", back_populates="sales_return", cascade="all, delete-orphan")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['subtotal', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['party_name'] = self.party.name if self.party else ""
        return d


class SalesReturnItem(Base):
    """Line item in a sales return."""
    __tablename__ = "sales_return_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    return_id = Column(Integer, ForeignKey("sales_returns.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    item_description = Column(String(255), nullable=False)
    quantity = Column(Numeric(12, 3), default=Decimal("1.000"), nullable=False)
    unit_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    sales_return = relationship("SalesReturn", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['quantity', 'unit_price', 'tax_rate', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        return d


class PurchaseReturn(Base):
    """Purchase Return (Debit Note) header."""
    __tablename__ = "purchase_returns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    return_number = Column(String(50), unique=True, nullable=False, index=True)
    return_date = Column(Date, nullable=False, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    subtotal = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)

    reason_category = Column(String(50), default="Purchase Return")
    original_invoice_no = Column(String(50), nullable=True)
    original_invoice_date = Column(Date, nullable=True)
    adjustment_mode = Column(String(50), default="Debit Note")
    adjustment_ref = Column(String(100), nullable=True)
    returned_via = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    party = relationship("Party", foreign_keys=[party_id])
    purchase_order = relationship("PurchaseOrder", foreign_keys=[po_id])
    items = relationship("PurchaseReturnItem", back_populates="purchase_return", cascade="all, delete-orphan")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['subtotal', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['party_name'] = self.party.name if self.party else ""
        return d


class PurchaseReturnItem(Base):
    """Line item in a purchase return."""
    __tablename__ = "purchase_return_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    return_id = Column(Integer, ForeignKey("purchase_returns.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    item_description = Column(String(255), nullable=False)
    quantity = Column(Numeric(12, 3), default=Decimal("1.000"), nullable=False)
    unit_price = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    purchase_return = relationship("PurchaseReturn", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['quantity', 'unit_price', 'tax_rate', 'tax_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        return d


class AppUser(Base):
    """Application user for login/authentication (billing module)."""
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(500), nullable=False)
    role = Column(String(20), default="user", nullable=False)  # admin, manager, user
    full_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        d.pop('password_hash', None)  # Never expose password hash
        return d


class ActivityLog(Base):
    """Audit trail for user actions."""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("app_users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    module = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

    user = relationship("AppUser", foreign_keys=[user_id])


# =============================================================================
# EXPENSE TRACKING MODELS
# =============================================================================

class ExpenseCategory(Base):
    """Predefined or user-created expense categories (Rent, Salary, Transport, etc.)."""
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)  # True for built-in categories
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    expenses = relationship("Expense", back_populates="category")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Expense(Base):
    """Business expense record (rent, salary, transport, utility, etc.)."""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_number = Column(String(50), unique=True, nullable=False, index=True)
    expense_date = Column(Date, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="SET NULL"), nullable=True)  # Optional payee

    description = Column(String(500), nullable=False)
    amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    gst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    payment_mode = Column(String(50), nullable=True)  # Cash, Bank Transfer, UPI, Cheque
    reference_no = Column(String(100), nullable=True)  # Bill/Receipt reference
    notes = Column(Text, nullable=True)
    receipt_image_path = Column(String(500), nullable=True)

    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    category = relationship("ExpenseCategory", back_populates="expenses")
    party = relationship("Party", foreign_keys=[party_id])

    __table_args__ = (
        Index("idx_expense_date_cat", "expense_date", "category_id"),
    )

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['amount', 'gst_amount', 'total_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['category_name'] = self.category.name if self.category else "Uncategorized"
        d['party_name'] = self.party.name if self.party else ""
        return d


# =============================================================================
# CASH & BANK BOOK MODELS
# =============================================================================

class BankAccount(Base):
    """Bank accounts for Cash & Bank Book tracking."""
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_name = Column(String(200), nullable=False, index=True)  # e.g. "SBI Current A/C", "Cash-in-Hand"
    account_type = Column(String(20), nullable=False, default="Bank")  # Cash, Bank
    bank_name = Column(String(200), nullable=True)
    account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(20), nullable=True)
    branch = Column(String(200), nullable=True)
    opening_balance = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    opening_balance_date = Column(Date, nullable=True, default=date.today)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    transactions = relationship(
        "CashBankTransaction",
        back_populates="account",
        cascade="all, delete-orphan",
        foreign_keys="[CashBankTransaction.account_id]"
    )

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        d['opening_balance'] = float(self.opening_balance) if self.opening_balance is not None else 0.0
        return d


class CashBankTransaction(Base):
    """Individual receipt/payment transaction in Cash or Bank book."""
    __tablename__ = "cash_bank_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    txn_date = Column(Date, nullable=False, index=True)
    txn_type = Column(String(20), nullable=False)  # Receipt (Money-In), Payment (Money-Out), Contra (Transfer)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="SET NULL"), nullable=True)

    description = Column(String(500), nullable=False)
    receipt_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)  # Money In
    payment_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)  # Money Out

    reference_no = Column(String(100), nullable=True)  # Cheque No, UTR, UPI Ref
    voucher_id = Column(Integer, ForeignKey("vouchers.id", ondelete="SET NULL"), nullable=True)  # Link to voucher
    contra_account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True)  # For contra entries
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    account = relationship("BankAccount", back_populates="transactions", foreign_keys=[account_id])
    party = relationship("Party", foreign_keys=[party_id])
    voucher = relationship("Voucher", foreign_keys=[voucher_id])
    contra_account = relationship("BankAccount", foreign_keys=[contra_account_id])

    __table_args__ = (
        Index("idx_cashbank_date_type", "txn_date", "txn_type"),
        Index("idx_cashbank_account_date", "account_id", "txn_date"),
    )

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for k in ['receipt_amount', 'payment_amount']:
            val = getattr(self, k)
            d[k] = float(val) if val is not None else 0.0
        d['account_name'] = self.account.account_name if self.account else ""
        d['party_name'] = self.party.name if self.party else ""
        return d


class VoucherAllocation(Base):
    """Stores bill-by-bill payment allocations against invoices (BUG-08)."""
    __tablename__ = "voucher_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_voucher_id = Column(Integer, ForeignKey("vouchers.id", ondelete="CASCADE"), nullable=True, index=True)
    invoice_voucher_id = Column(Integer, ForeignKey("vouchers.id", ondelete="CASCADE"), nullable=True, index=True)
    allocated_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    allocation_date = Column(Date, default=date.today, nullable=False)
    allocation_type = Column(String(30), default="FIFO", nullable=False)  # FIFO, REFERENCE, OPENING
    created_at = Column(DateTime, default=datetime.now)

    party = relationship("Party")
    payment_voucher = relationship("Voucher", foreign_keys=[payment_voucher_id])
    invoice_voucher = relationship("Voucher", foreign_keys=[invoice_voucher_id])

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        d["allocated_amount"] = float(self.allocated_amount) if self.allocated_amount is not None else 0.0
        return d


class User(Base):
    """User accounts and RBAC permissions."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(30), default="Viewer", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name or "",
            "role": self.role,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class PeriodLock(Base):
    """Accounting period lock to prevent modifications before date."""
    __tablename__ = "period_locks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    locked_until_date = Column(Date, nullable=False)
    locked_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=True)
    locked_at = Column(DateTime, default=datetime.now)

    locked_by = relationship("User", foreign_keys=[locked_by_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "locked_until_date": self.locked_until_date,
            "reason": self.reason or "",
            "locked_by_user_id": self.locked_by_user_id,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None
        }


class AuditLog(Base):
    """Security and compliance audit trail."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(100), default="System", nullable=False)
    action = Column(String(50), nullable=False)
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(Integer, nullable=True)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if self.timestamp:
            d["timestamp"] = self.timestamp.isoformat()
        return d


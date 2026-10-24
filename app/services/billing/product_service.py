"""
Product / Inventory Service
CRUD operations and stock management for the Products table.
"""
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_, func

from app.database.connection import get_session
from app.database.models import Product, Party
from app.services.validation_helpers import validate_model_dict


def get_all_products(
    search: str = None,
    category: str = None,
    active_only: bool = True,
    low_stock_only: bool = False,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """Fetch products with optional filters."""
    with get_session() as session:
        query = session.query(Product)
        if active_only:
            query = query.filter(Product.is_active == True)
        if category and category != "All":
            query = query.filter(Product.category == category)
        if low_stock_only:
            query = query.filter(Product.stock_quantity <= Product.low_stock_threshold)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Product.name.ilike(pattern),
                    Product.hsn_code.ilike(pattern),
                    Product.barcode.ilike(pattern),
                    Product.category.ilike(pattern),
                )
            )
        products = query.order_by(Product.name).limit(limit).all()
        return [p.to_dict() for p in products]


def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single product by ID."""
    with get_session() as session:
        product = session.query(Product).filter(Product.id == product_id).first()
        if product:
            d = product.to_dict()
            d['supplier_name'] = product.supplier.name if product.supplier else ""
            return d
        return None


from app.services.validation_helpers import (
    parse_decimal, normalize_name, enforce_max_length
)
from app.database.models import CompanyProfile


def _validate_product_fields(
    data: Dict[str, Any], session, product_id: Optional[int] = None
) -> Dict[str, Any]:
    """Shared validator for Product create and update (BUG-09, BUG-27, BUG-28, BUG-29)."""
    cleaned = dict(data)

    if "name" in cleaned or product_id is None:
        name = normalize_name(cleaned.get("name", ""))
        if not name:
            raise ValueError("Product name is required.")
        enforce_max_length("Product name", name, 200)
        cleaned["name"] = name

        q = session.query(Product).filter(
            func.lower(Product.name) == name.lower(),
            Product.is_active.is_(True)
        )
        if product_id:
            q = q.filter(Product.id != product_id)
        if q.first():
            raise ValueError(f"Product with name '{name}' already exists.")

    if "barcode" in cleaned:
        raw_b = cleaned.get("barcode")
        if raw_b and str(raw_b).strip():
            barcode = str(raw_b).strip()
            enforce_max_length("Barcode/SKU", barcode, 100)
            cleaned["barcode"] = barcode

            q = session.query(Product).filter(
                Product.barcode == barcode,
                Product.is_active.is_(True)
            )
            if product_id:
                q = q.filter(Product.id != product_id)
            if q.first():
                raise ValueError(f"Product with barcode/SKU '{barcode}' already exists.")
        else:
            cleaned["barcode"] = None

    if "price" in cleaned or product_id is None:
        price = parse_decimal(cleaned.get("price", "0.00"))
        if price < Decimal("0.00"):
            raise ValueError("Selling price cannot be negative.")
        cleaned["price"] = price

    if "purchase_price" in cleaned:
        raw_pp = cleaned.get("purchase_price")
        if raw_pp is not None and str(raw_pp).strip() != "":
            pp = parse_decimal(raw_pp)
            if pp < Decimal("0.00"):
                raise ValueError("Purchase price cannot be negative.")
            cleaned["purchase_price"] = pp
        else:
            cleaned["purchase_price"] = None

    if "wholesale_price" in cleaned:
        raw_wp = cleaned.get("wholesale_price")
        if raw_wp is not None and str(raw_wp).strip() != "":
            wp = parse_decimal(raw_wp)
            if wp < Decimal("0.00"):
                raise ValueError("Wholesale price cannot be negative.")
            cleaned["wholesale_price"] = wp
        else:
            cleaned["wholesale_price"] = None

    if "tax_rate" in cleaned or product_id is None:
        tax_rate = parse_decimal(cleaned.get("tax_rate", "18.00"))
        if tax_rate < Decimal("0.00") or tax_rate > Decimal("100.00"):
            raise ValueError("Tax rate must be between 0% and 100%.")
        cleaned["tax_rate"] = tax_rate

    if "stock_quantity" in cleaned or product_id is None:
        stock = parse_decimal(cleaned.get("stock_quantity", "0.000"))
        if stock < Decimal("0.00"):
            comp = session.query(CompanyProfile).first()
            allow_neg = getattr(comp, "allow_negative_stock", False) if comp else False
            if not allow_neg:
                raise ValueError("Stock quantity cannot be negative.")
        cleaned["stock_quantity"] = stock

    if "low_stock_threshold" in cleaned:
        raw_lst = cleaned.get("low_stock_threshold")
        if raw_lst is not None and str(raw_lst).strip() != "":
            lst = parse_decimal(raw_lst)
            if lst < Decimal("0.00"):
                raise ValueError("Low stock threshold cannot be negative.")
            cleaned["low_stock_threshold"] = lst
        else:
            cleaned["low_stock_threshold"] = Decimal("10.000")

    if "hsn_code" in cleaned and cleaned["hsn_code"]:
        hsn = str(cleaned["hsn_code"]).strip()
        enforce_max_length("HSN code", hsn, 20)
        cleaned["hsn_code"] = hsn or None

    if "description" in cleaned and cleaned["description"]:
        desc_text = str(cleaned["description"]).strip()
        enforce_max_length("Description", desc_text, 500)
        cleaned["description"] = desc_text or None

    if "category" in cleaned and cleaned["category"]:
        cat_text = str(cleaned["category"]).strip()
        enforce_max_length("Category", cat_text, 100)
        cleaned["category"] = cat_text or None

    return cleaned


def create_product(data: Dict[str, Any]) -> Product:
    """Create a new product with full validation."""
    validate_model_dict(Product, data)
    with get_session() as session:
        validated = _validate_product_fields(data, session=session)
        product = Product(**validated)
        session.add(product)
        session.flush()
        session.refresh(product)
        return product


def update_product(product_id: int, data: Dict[str, Any]) -> Optional[Product]:
    """Update an existing product with full validation (BUG-09)."""
    validate_model_dict(Product, data)
    with get_session() as session:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None

        validated = _validate_product_fields(data, session=session, product_id=product_id)

        for key, value in validated.items():
            if hasattr(product, key) and key not in ("id", "created_at"):
                setattr(product, key, value)

        session.flush()
        session.refresh(product)
        return product


def delete_product(product_id: int) -> bool:
    """Soft-delete a product (set is_active=False)."""
    with get_session() as session:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            return False
        product.is_active = False
        return True


def update_stock(product_id: int, quantity: float, transaction_type: str = 'sale') -> bool:
    """
    Update stock quantity.
    transaction_type: 'sale' (decrease), 'purchase' (increase), 'return' (increase)
    """
    with get_session() as session:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            return False
        current = float(product.stock_quantity or 0)
        if transaction_type == 'sale':
            new_stock = current - quantity
        elif transaction_type in ('purchase', 'return'):
            new_stock = current + quantity
        else:
            raise ValueError(f"Invalid transaction type: {transaction_type}")
        if new_stock < 0:
            return False
        product.stock_quantity = Decimal(str(new_stock))
        return True


def check_stock(product_id: int, quantity: float) -> bool:
    """Check if sufficient stock is available."""
    with get_session() as session:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            return False
        return float(product.stock_quantity or 0) >= quantity


def get_categories() -> List[str]:
    """Get distinct product categories."""
    with get_session() as session:
        rows = session.query(Product.category).filter(
            Product.category.isnot(None), Product.is_active == True
        ).distinct().order_by(Product.category).all()
        return [r[0] for r in rows if r[0]]


def get_low_stock_count() -> int:
    """Get count of products below low-stock threshold."""
    with get_session() as session:
        return session.query(Product).filter(
            Product.stock_quantity <= Product.low_stock_threshold,
            Product.is_active == True
        ).count()

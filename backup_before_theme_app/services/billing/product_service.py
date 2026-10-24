"""
Product / Inventory Service
CRUD operations and stock management for the Products table.
"""
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_, func

from app.database.connection import get_session
from app.database.models import Product, Party


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


def create_product(data: Dict[str, Any]) -> Product:
    """Create a new product."""
    with get_session() as session:
        product = Product(
            name=data.get("name", "").strip(),
            hsn_code=data.get("hsn_code", "").strip() or None,
            description=data.get("description", "").strip() or None,
            unit=data.get("unit", "PCS"),
            price=Decimal(str(data.get("price", "0.00"))),
            purchase_price=Decimal(str(data.get("purchase_price", "0.00"))) if data.get("purchase_price") else None,
            wholesale_price=Decimal(str(data.get("wholesale_price", "0.00"))) if data.get("wholesale_price") else None,
            tax_rate=Decimal(str(data.get("tax_rate", "18.00"))),
            stock_quantity=Decimal(str(data.get("stock_quantity", "0.000"))),
            low_stock_threshold=Decimal(str(data.get("low_stock_threshold", "10.000"))),
            barcode=data.get("barcode", "").strip() or None,
            category=data.get("category", "").strip() or None,
            supplier_id=data.get("supplier_id") or None,
        )
        if not product.name:
            raise ValueError("Product name is required.")
        if product.price < Decimal("0.00"):
            raise ValueError("Selling price cannot be negative.")
        if product.purchase_price is not None and product.purchase_price < Decimal("0.00"):
            raise ValueError("Purchase price cannot be negative.")
        if product.stock_quantity < Decimal("0.00"):
            raise ValueError("Stock quantity cannot be negative.")

        # Check duplicate name
        existing_p = session.query(Product).filter(
            func.lower(Product.name) == product.name.lower(),
            Product.is_active == True
        ).first()
        if existing_p:
            raise ValueError(f"Product with name '{product.name}' already exists.")

        # Check duplicate barcode/SKU
        if product.barcode:
            existing_b = session.query(Product).filter(
                Product.barcode == product.barcode,
                Product.is_active == True
            ).first()
            if existing_b:
                raise ValueError(f"Product with barcode/SKU '{product.barcode}' already exists.")

        session.add(product)
        session.flush()
        session.refresh(product)
        return product


def update_product(product_id: int, data: Dict[str, Any]) -> Optional[Product]:
    """Update an existing product."""
    with get_session() as session:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None
        for key, value in data.items():
            if hasattr(product, key) and key not in ("id", "created_at"):
                if key in ('price', 'purchase_price', 'wholesale_price', 'tax_rate',
                           'stock_quantity', 'low_stock_threshold'):
                    value = Decimal(str(value)) if value is not None else None
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

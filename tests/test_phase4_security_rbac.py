"""
Unit Tests for Phase 4: Security, RBAC, Audit Trail & Period Locking.
Verifies:
1. Scrypt password hashing with cryptographic salt & constant-time comparison.
2. Role-Based Access Control (Admin, Accountant, Billing, Viewer).
3. Brute-force lockout (5 failed attempts locks account for 15 minutes).
4. Audit trail logging & query retrieval.
5. Period locking enforcement (blocks creating or modifying transactions on or before lock date).
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.database.connection import get_session
from app.database.models import Party, Product, User, PeriodLock
from app.services.auth_service import (
    hash_password, verify_password, create_user, authenticate,
    has_permission, enforce_permission, lock_accounting_period,
    check_period_unlocked, get_current_user, set_current_user,
    ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_BILLING, ROLE_VIEWER,
    PERM_MANAGE_USERS, PERM_VIEW_PNL, PERM_CREATE_INVOICE, PERM_LOCK_PERIOD
)
from app.services.audit_service import log_audit, get_audit_trail
from app.services.billing import invoice_service


def test_scrypt_password_hashing_and_verification():
    """Verify scrypt hashing produces unique salts and verifies correctly."""
    pwd = "SecurePassword@123"
    h1, salt1 = hash_password(pwd)
    h2, salt2 = hash_password(pwd)

    # Different salts must yield different hashes
    assert salt1 != salt2
    assert h1 != h2

    # Verification must succeed for correct password and fail for wrong password
    assert verify_password(pwd, h1, salt1) is True
    assert verify_password(pwd, h2, salt2) is True
    assert verify_password("WrongPassword!", h1, salt1) is False


def test_user_creation_and_rbac_permissions(clean_db):
    """Verify role-based access permissions across roles."""
    with get_session() as s:
        s.query(User).filter(User.username.in_(["admin_test", "acct_test", "bill_test", "view_test"])).delete()

    admin_u = create_user({"username": "admin_test", "password": "password123", "role": ROLE_ADMIN})
    acct_u = create_user({"username": "acct_test", "password": "password123", "role": ROLE_ACCOUNTANT})
    bill_u = create_user({"username": "bill_test", "password": "password123", "role": ROLE_BILLING})
    view_u = create_user({"username": "view_test", "password": "password123", "role": ROLE_VIEWER})

    # Admin holds all permissions
    assert has_permission(PERM_MANAGE_USERS, admin_u) is True
    assert has_permission(PERM_VIEW_PNL, admin_u) is True
    assert has_permission(PERM_CREATE_INVOICE, admin_u) is True
    assert has_permission(PERM_LOCK_PERIOD, admin_u) is True

    # Accountant can view P&L and create invoices, but cannot manage users or lock periods
    assert has_permission(PERM_MANAGE_USERS, acct_u) is False
    assert has_permission(PERM_VIEW_PNL, acct_u) is True
    assert has_permission(PERM_CREATE_INVOICE, acct_u) is True
    assert has_permission(PERM_LOCK_PERIOD, acct_u) is False

    # Billing operator can only create invoices
    assert has_permission(PERM_VIEW_PNL, bill_u) is False
    assert has_permission(PERM_CREATE_INVOICE, bill_u) is True

    # Viewer cannot create invoices or manage users
    assert has_permission(PERM_CREATE_INVOICE, view_u) is False
    with pytest.raises(PermissionError):
        enforce_permission(PERM_CREATE_INVOICE, view_u)


def test_brute_force_account_lockout(clean_db):
    """Verify 5 failed attempts locks user account for 15 minutes."""
    with get_session() as s:
        s.query(User).filter(User.username == "lockout_target").delete()

    create_user({"username": "lockout_target", "password": "TargetPassword123", "role": ROLE_VIEWER})

    # 4 failed attempts should fail with warning
    for i in range(4):
        ok, u, msg = authenticate("lockout_target", "WrongPassword")
        assert ok is False
        assert "attempt(s) remaining" in msg

    # 5th failed attempt triggers lockout
    ok5, u5, msg5 = authenticate("lockout_target", "WrongPassword")
    assert ok5 is False
    assert "locked for 15 minutes" in msg5.lower()

    # 6th attempt with CORRECT password must still be rejected due to lockout
    ok6, u6, msg6 = authenticate("lockout_target", "TargetPassword123")
    assert ok6 is False
    assert "locked" in msg6.lower()


def test_audit_trail_logging_and_query(clean_db):
    """Verify recording and querying audit trail entries."""
    admin_dict = {"id": 1, "username": "super_admin", "role": ROLE_ADMIN}
    set_current_user(admin_dict)

    entry_id = log_audit(
        action="UPDATE",
        table_name="parties",
        record_id=42,
        old_values={"credit_limit": 50000},
        new_values={"credit_limit": 100000},
        notes="Approved credit limit increase by CA"
    )
    assert entry_id is not None

    logs = get_audit_trail(table_name="parties", record_id=42)
    assert len(logs) >= 1
    recent = logs[0]
    assert recent["action"] == "UPDATE"
    assert recent["username"] == "super_admin"
    assert "100000" in recent["new_values"]
    assert "Approved credit limit" in recent["notes"]


def test_period_locking_blocks_transactions(clean_db):
    """Verify creating an invoice in a locked period raises ValueError."""
    admin_dict = {"id": 1, "username": "admin", "role": ROLE_ADMIN}
    set_current_user(admin_dict)

    # Lock period up to 31 March 2026
    lock_date = date(2026, 3, 31)
    lock_accounting_period(lock_date, reason="FY 2025-26 Year-End Books Closed")

    with get_session() as s:
        p = Party(name="Locked Period Test Cust", party_type="Customer", state_code="19")
        s.add(p)
        s.flush()
        pid = p.id

    # 1. Attempt to create invoice on 15 March 2026 (inside locked period) -> must fail!
    with pytest.raises(ValueError, match="Accounting period is locked up to 31-03-2026"):
        invoice_service.create_invoice({
            "party_id": pid,
            "invoice_date": date(2026, 3, 15),
            "items": [{"item_description": "Past Item", "quantity": 1, "unit_price": 1000, "gst_rate_pct": 18}],
            "status": "final"
        })

    # 2. Creating invoice on 15 April 2026 (outside locked period) -> must succeed!
    inv_ok = invoice_service.create_invoice({
        "party_id": pid,
        "invoice_date": date(2026, 4, 15),
        "items": [{"item_description": "New FY Item", "quantity": 1, "unit_price": 1000, "gst_rate_pct": 18}],
        "status": "final"
    })
    assert inv_ok is not None
    assert inv_ok.invoice_date == date(2026, 4, 15)

"""
Authentication, Role-Based Access Control (RBAC), and Period Locking Service (Phase 4).
Implements:
1. Roles: Admin, Accountant, Billing, Viewer.
2. Scrypt-based salted password hashing.
3. Brute-force lockout (5 failed attempts locks for 15 minutes).
4. Permission checking helpers for service layer enforcement.
5. Period locking (blocks creating/modifying transactions in locked periods).
"""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, Tuple, List

from app.database.connection import get_session
from app.database.models import User, PeriodLock

logger = logging.getLogger("BillFlow.Auth")

# Standard RBAC Roles
ROLE_ADMIN = "Admin"
ROLE_ACCOUNTANT = "Accountant"
ROLE_BILLING = "Billing"
ROLE_VIEWER = "Viewer"

# Permission Tokens
PERM_MANAGE_USERS = "manage_users"
PERM_VIEW_PNL = "view_pnl"
PERM_LOCK_PERIOD = "lock_period"
PERM_POST_VOUCHERS = "post_vouchers"
PERM_CREATE_INVOICE = "create_invoice"
PERM_CANCEL_INVOICE = "cancel_invoice"
PERM_DELETE_DATA = "delete_data"
PERM_RESTORE_DB = "restore_db"

ROLE_PERMISSIONS = {
    ROLE_ADMIN: {
        PERM_MANAGE_USERS, PERM_VIEW_PNL, PERM_LOCK_PERIOD,
        PERM_POST_VOUCHERS, PERM_CREATE_INVOICE, PERM_CANCEL_INVOICE,
        PERM_DELETE_DATA, PERM_RESTORE_DB
    },
    ROLE_ACCOUNTANT: {
        PERM_VIEW_PNL, PERM_POST_VOUCHERS, PERM_CREATE_INVOICE,
        PERM_CANCEL_INVOICE
    },
    ROLE_BILLING: {
        PERM_CREATE_INVOICE
    },
    ROLE_VIEWER: set()
}

_current_session_user: Optional[Dict[str, Any]] = None


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Generates a secure scrypt hash with a cryptographic 128-bit salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384,
        r=8,
        p=1
    ).hex()
    return hashed, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies password using constant-time comparison against scrypt digest."""
    candidate_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384,
        r=8,
        p=1
    ).hex()
    return hmac.compare_digest(candidate_hash, stored_hash)


def get_current_user() -> Optional[Dict[str, Any]]:
    """Returns currently authenticated user profile in the active session."""
    global _current_session_user
    return _current_session_user


def set_current_user(user_dict: Optional[Dict[str, Any]]):
    """Sets the active session user context."""
    global _current_session_user
    _current_session_user = user_dict


def ensure_default_admin():
    """Seeds default admin user if no users exist in database."""
    with get_session() as session:
        count = session.query(User).count()
        if count == 0:
            pw_hash, salt = hash_password("admin123")
            admin_user = User(
                username="admin",
                password_hash=pw_hash,
                salt=salt,
                full_name="System Administrator",
                role=ROLE_ADMIN,
                is_active=True
            )
            session.add(admin_user)
            session.commit()
            logger.info("Created default administrator account 'admin'.")


def create_user(data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new user profile with hashed password and assigned role."""
    uname = (data.get("username") or "").strip().lower()
    raw_pwd = data.get("password") or ""
    role = data.get("role") or ROLE_VIEWER
    full_name = (data.get("full_name") or "").strip()

    if not uname or len(uname) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if not raw_pwd or len(raw_pwd) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Invalid role '{role}'. Allowed: {list(ROLE_PERMISSIONS.keys())}")

    with get_session() as session:
        existing = session.query(User).filter(User.username == uname).first()
        if existing:
            raise ValueError(f"User '{uname}' already exists.")

        p_hash, salt = hash_password(raw_pwd)
        user = User(
            username=uname,
            password_hash=p_hash,
            salt=salt,
            full_name=full_name,
            role=role,
            is_active=True
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.to_dict()


def authenticate(username: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Authenticates user with brute-force lockout protection.
    Locks account for 15 minutes after 5 consecutive failed attempts.
    """
    ensure_default_admin()
    uname = (username or "").strip().lower()

    with get_session() as session:
        user = session.query(User).filter(User.username == uname).first()
        if not user:
            return False, None, "Invalid username or password."

        if not user.is_active:
            return False, None, "This user account has been deactivated."

        now = datetime.now()
        if user.locked_until and user.locked_until > now:
            diff = int((user.locked_until - now).total_seconds() / 60) + 1
            return False, None, f"Account locked due to failed attempts. Try again in {diff} minute(s)."

        if not verify_password(password, user.password_hash, user.salt):
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
                logger.warning(f"User '{uname}' locked out for 15 minutes after 5 failed attempts.")
                session.commit()
                return False, None, "Account locked for 15 minutes due to 5 failed attempts."
            session.commit()
            rem = 5 - user.failed_attempts
            return False, None, f"Invalid username or password. ({rem} attempt(s) remaining before lockout)"

        # Successful authentication
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = now
        session.commit()

        u_dict = user.to_dict()
        set_current_user(u_dict)
        return True, u_dict, None


def has_permission(permission: str, user: Optional[Dict[str, Any]] = None) -> bool:
    """Checks whether the user holds the specified permission token."""
    if user is None:
        user = get_current_user()
    if not user:
        # If no authentication session is established, default to full Admin in offline single-user desktop mode
        return True

    role = user.get("role", ROLE_VIEWER)
    allowed_perms = ROLE_PERMISSIONS.get(role, set())
    return permission in allowed_perms


def enforce_permission(permission: str, user: Optional[Dict[str, Any]] = None):
    """Raises PermissionError if the current user lacks the required permission."""
    if not has_permission(permission, user):
        role = (user or get_current_user() or {}).get("role", "Unknown")
        raise PermissionError(f"Access denied: Role '{role}' lacks '{permission}' permission.")


# --- Period Locking ---

def lock_accounting_period(locked_until_date: date, reason: str = "", user_id: Optional[int] = None) -> Dict[str, Any]:
    """Admin-only: locks accounting period up to specified date."""
    enforce_permission(PERM_LOCK_PERIOD)
    with get_session() as session:
        lock = session.query(PeriodLock).order_by(PeriodLock.id.desc()).first()
        if not lock:
            lock = PeriodLock(locked_until_date=locked_until_date, reason=reason, locked_by_user_id=user_id)
            session.add(lock)
        else:
            lock.locked_until_date = locked_until_date
            lock.reason = reason
            lock.locked_by_user_id = user_id
            lock.locked_at = datetime.now()
        session.commit()
        session.refresh(lock)
        logger.info(f"Accounting period locked up to {locked_until_date}. Reason: {reason}")
        return lock.to_dict()


def get_current_period_lock() -> Optional[Dict[str, Any]]:
    """Returns currently active period lock if any."""
    with get_session() as session:
        lock = session.query(PeriodLock).order_by(PeriodLock.id.desc()).first()
        return lock.to_dict() if lock else None


def check_period_unlocked(txn_date: date):
    """
    Validates that txn_date is outside any locked accounting period.
    Raises ValueError if txn_date falls within a locked period.
    """
    with get_session() as session:
        lock = session.query(PeriodLock).order_by(PeriodLock.id.desc()).first()
        if lock and txn_date <= lock.locked_until_date:
            raise ValueError(
                f"Accounting period is locked up to {lock.locked_until_date.strftime('%d-%m-%Y')} "
                f"({lock.reason or 'Year-end freeze'}). Cannot post or modify transactions on or before this date."
            )

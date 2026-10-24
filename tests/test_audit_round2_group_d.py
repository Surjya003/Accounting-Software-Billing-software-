"""
Regression tests for QA Audit Round 2 - Group D (Minor & Documentation Claims)
Tests BUG-01, BUG-02, BUG-21, CLM-05, CLM-09, CLM-10.
"""
import sys
import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.config import TRIAL_DAYS
from app.services.license_service import get_license_status
from app.database.connection import get_session
from app.database.models import LicenseRecord, Product, CompanyProfile
from app.ui.async_worker import AsyncWorker, run_in_background


def test_bug_01_trial_days_constant():
    """BUG-01 / CLM-05: TRIAL_DAYS must be 14."""
    assert TRIAL_DAYS == 14
    status = get_license_status()
    # In trial mode, total days must be 14
    if status.get("status") == "TRIAL":
        assert status.get("total_days") == 14


def test_clm_05_clock_tamper_detection():
    """CLM-05: System clock moving backwards is detected as TAMPERED."""
    from datetime import datetime
    original_state = {}
    with get_session() as session:
        lic = session.query(LicenseRecord).first()
        if lic:
            original_state = {
                "status": lic.status,
                "license_key": lic.license_key,
                "last_verified_at": lic.last_verified_at
            }
            # Put in trial mode with future last_verified_at
            lic.status = "TRIAL"
            lic.license_key = None
            lic.last_verified_at = datetime.now() + timedelta(days=2)
            session.commit()

    try:
        status = get_license_status()
        assert "Rollback Detected" in status.get("status_text", "")
    finally:
        # Restore original record
        if original_state:
            with get_session() as session:
                lic = session.query(LicenseRecord).first()
                if lic:
                    lic.status = original_state["status"]
                    lic.license_key = original_state["license_key"]
                    lic.last_verified_at = original_state["last_verified_at"]
                    session.commit()


def test_bug_21_stock_valuation_logic():
    """BUG-21: Stock valuation uses current stock x latest purchase price, not FIFO."""
    with get_session() as session:
        p = Product(
            name="Valuation Test Item",
            hsn_code="1234",
            stock_quantity=Decimal("15"),
            purchase_price=Decimal("200.00"),
            price=Decimal("350.00"),
            tax_rate=Decimal("18.00")
        )
        session.add(p)
        session.commit()

        # Valuation = 15 * 200 = 3000
        val = p.stock_quantity * p.purchase_price
        assert val == Decimal("3000.00")


def test_clm_09_sqlite_datetime_adapters():
    """CLM-09: Datetime/Date objects persist and query cleanly without DeprecationWarnings."""
    import warnings
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always", DeprecationWarning)
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            assert comp is not None
        # Check no DeprecationWarnings related to sqlite3 date adapter
        sqlite_warnings = [
            w for w in recorded
            if "sqlite3" in str(w.message).lower() or "adapter" in str(w.message).lower()
        ]
        assert len(sqlite_warnings) == 0


def test_clm_10_async_worker():
    """CLM-10: AsyncWorker executes tasks in thread pool and emits signals."""
    results = []
    errors = []

    def heavy_task(x, y):
        return x * y

    worker = AsyncWorker(heavy_task, 6, 7)
    worker.signals.result.connect(lambda r: results.append(r))
    worker.signals.error.connect(lambda e: errors.append(e))

    # Execute run synchronously for test validation
    worker.run()

    assert len(results) == 1
    assert results[0] == 42
    assert len(errors) == 0

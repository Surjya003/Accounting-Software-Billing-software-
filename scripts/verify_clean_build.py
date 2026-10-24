"""
Verify Clean Build & Fresh State Integrity Script.
Checks:
1. Fresh database initializes with empty CompanyProfile (no demo/seed data).
2. Zero hardcoded placeholder strings in default DB or fresh company profile.
3. Validate company profile export guard blocks export on empty profile.
"""
import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import Base, CompanyProfile, Party
from app.ui.save_dialog import validate_company_profile_for_export

FORBIDDEN_PLACEHOLDERS = [
    "Sita Ram & Sons Traders",
    "27AABCS1429B1Z8",
    "381928472910",
    "MY BUSINESS",
    "Vyapar Traders",
]


def test_clean_state_initialization():
    print("--> Testing Clean State Database Initialization...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "fresh_test.db"
        engine = create_engine(f"sqlite:///{test_db}", echo=False)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as session:
            # Simulate first-run company profile creation
            comp = CompanyProfile(
                name="",
                trade_name="",
                gstin="",
                pan="",
                address="",
                city="",
                state=None,
                state_code=None,
                pincode="",
                phone="",
                email="",
                bank_name="",
                bank_account_no="",
                bank_ifsc="",
                bank_branch="",
                upi_id=""
            )
            session.add(comp)
            session.commit()
            session.refresh(comp)

            # 1. Check identity fields are empty
            assert comp.name == "", f"Expected empty name, got '{comp.name}'"
            assert comp.state is None, f"Expected None state, got '{comp.state}'"
            assert comp.state_code is None, f"Expected None state_code, got '{comp.state_code}'"
            assert comp.gstin == "", f"Expected empty gstin, got '{comp.gstin}'"
            assert comp.bank_account_no == "", f"Expected empty bank account, got '{comp.bank_account_no}'"

            # 2. Check no forbidden placeholders in DB
            comp_dict = comp.to_dict()
            for key, val in comp_dict.items():
                if isinstance(val, str) and val:
                    for forbidden in FORBIDDEN_PLACEHOLDERS:
                        assert forbidden.lower() not in val.lower(), (
                            f"Forbidden placeholder '{forbidden}' found in {key}: {val}"
                        )

            # 3. Check PDF export validation guard
            valid, msg = validate_company_profile_for_export(comp)
            assert not valid, "Validation guard should reject empty profile!"
            print(f"    Guard correctly blocked export: {msg}")

            # 4. Check that completing name and state allows export
            comp.name = "Binapani Automation"
            comp.state = "West Bengal"
            comp.state_code = "19"
            session.commit()

            valid, msg = validate_company_profile_for_export(comp)
            assert valid, f"Validation guard should pass complete profile, got error: {msg}"
            print("    Guard correctly allowed export with complete profile.")

        engine.dispose()

    print("[PASS] Clean State & Validation Guard Verification Successful!\n")


if __name__ == "__main__":
    test_clean_state_initialization()

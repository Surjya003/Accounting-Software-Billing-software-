"""
Hardware-Locked Offline Licensing and Trial Management Service
"""
import hashlib
import hmac
import platform
import subprocess
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, Any, Tuple, Optional

from app.database.connection import get_session
from app.database.models import LicenseRecord

# Master secret key known only to the vendor (used to sign license keys)
VENDOR_SECRET = b"VYAPAR_LEDGER_MASTER_SIGNING_KEY_2024_PRO_COMMERCIAL"
TRIAL_DAYS = 15

import functools

@functools.lru_cache(maxsize=1)
def get_machine_fingerprint() -> str:
    """
    Generates a deterministic, unique 16-character hardware identifier for this PC
    combining Windows MachineGuid / Motherboard UUID, MAC address, and Processor ID.
    """
    raw_parts = []
    
    # 1. Windows Machine GUID from Registry (Instant & Zero-overhead)
    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid:
                    raw_parts.append(str(guid).strip())
        except Exception:
            pass
            
    # 2. Node / MAC Address
    try:
        mac = str(uuid.getnode())
        raw_parts.append(mac)
    except Exception:
        pass
        
    # 3. Processor & System info
    raw_parts.append(platform.processor() or "CPU")
    raw_parts.append(platform.machine() or "x86_64")
    
    combined = ":".join(raw_parts)
    h = hashlib.sha256(combined.encode("utf-8")).hexdigest().upper()
    # Format into readable 4-part code: VYAP-XXXX-XXXX-XXXX
    return f"VYAP-{h[:4]}-{h[4:8]}-{h[8:12]}"

def generate_license_key(machine_id: str, company_name: str, expiry_date_str: str = "PERPETUAL") -> str:
    """
    Vendor tool function: Generates a signed activation key for a client.
    `expiry_date_str` can be 'PERPETUAL' or 'YYYY-MM-DD'.
    """
    clean_mach = machine_id.strip().upper()
    clean_comp = company_name.strip().upper()
    payload = f"{clean_mach}|{clean_comp}|{expiry_date_str}"
    
    sig = hmac.new(VENDOR_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    # Take 20 chars of signature + payload encoding
    # Format: [PERP/DATE_CODE]-[SIG1]-[SIG2]-[SIG3]-[SIG4]
    date_tag = "P" if expiry_date_str == "PERPETUAL" else expiry_date_str.replace("-", "")[2:]
    key = f"{date_tag}-{sig[:4]}-{sig[4:8]}-{sig[8:12]}-{sig[12:16]}"
    return key

def verify_license_key(machine_id: str, company_name: str, license_key: str) -> Tuple[bool, str, Optional[date]]:
    """
    Verifies if a license key is valid for this machine and company.
    Returns: (is_valid, message, expiry_date)
    """
    if not license_key or not license_key.strip():
        return False, "License key is empty", None
        
    key = license_key.strip().upper()
    parts = key.split("-")
    if len(parts) < 5:
        return False, "Invalid license key format", None
        
    date_tag = parts[0]
    if date_tag == "P":
        expiry_str = "PERPETUAL"
        exp_date = None
    else:
        try:
            # e.g. '251231' -> '2025-12-31'
            y = int("20" + date_tag[:2])
            m = int(date_tag[2:4])
            d = int(date_tag[4:6])
            exp_date = date(y, m, d)
            expiry_str = exp_date.isoformat()
        except Exception:
            return False, "Invalid expiry date code in license key", None
            
    expected_key = generate_license_key(machine_id, company_name, expiry_str)
    if key != expected_key:
        return False, "License key signature verification failed for this machine", None
        
    if exp_date and exp_date < date.today():
        return False, f"License expired on {exp_date.strftime('%d-%m-%Y')}", exp_date
        
    return True, "Valid License", exp_date

def get_license_status() -> Dict[str, Any]:
    """
    Checks the active licensing state of the application.
    """
    machine_id = get_machine_fingerprint()
    today = date.today()
    
    with get_session() as session:
        rec = session.query(LicenseRecord).first()
        if not rec:
            rec = LicenseRecord(
                machine_fingerprint=machine_id,
                status="TRIAL",
                trial_start_date=today
            )
            session.add(rec)
            session.commit()
            
        if rec.status == "ACTIVE" and rec.license_key:
            is_valid, msg, exp_date = verify_license_key(machine_id, rec.issued_to or "", rec.license_key)
            if is_valid:
                return {
                    "is_licensed": True,
                    "is_trial": False,
                    "machine_id": machine_id,
                    "issued_to": rec.issued_to,
                    "is_perpetual": rec.is_perpetual,
                    "expiry_date": rec.expiry_date,
                    "status_text": "Commercial License (Active)",
                    "days_remaining": (rec.expiry_date - today).days if rec.expiry_date else 99999
                }
            else:
                rec.status = "EXPIRED"
                session.commit()
                
        # Handle Trial Mode
        trial_start = rec.trial_start_date or today
        days_passed = (today - trial_start).days
        days_left = max(0, TRIAL_DAYS - days_passed)
        is_trial_active = days_passed < TRIAL_DAYS
        
        return {
            "is_licensed": False,
            "is_trial": is_trial_active,
            "machine_id": machine_id,
            "issued_to": None,
            "is_perpetual": False,
            "expiry_date": trial_start + timedelta(days=TRIAL_DAYS),
            "status_text": f"Free Trial ({days_left} days remaining)" if is_trial_active else "Trial Expired (License Required)",
            "days_remaining": days_left
        }

def activate_license(company_name: str, license_key: str) -> Tuple[bool, str]:
    """Activates the application with a valid offline license key."""
    machine_id = get_machine_fingerprint()
    is_valid, msg, exp_date = verify_license_key(machine_id, company_name, license_key)
    if not is_valid:
        return False, msg
        
    with get_session() as session:
        rec = session.query(LicenseRecord).first()
        if not rec:
            rec = LicenseRecord(machine_fingerprint=machine_id)
            session.add(rec)
            
        rec.machine_fingerprint = machine_id
        rec.license_key = license_key.strip().upper()
        rec.issued_to = company_name.strip()
        rec.activation_date = date.today()
        rec.expiry_date = exp_date
        rec.is_perpetual = (exp_date is None)
        rec.status = "ACTIVE"
        rec.last_verified_at = datetime.now()
        session.commit()
        
    return True, "License activated successfully!"

"""
Vendor Offline License Key Generator Tool
Used by the software vendor/owner to issue offline activation keys to customers.
"""
import sys
import argparse
from datetime import datetime, date

# Allow importing from project root
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.license_service import generate_license_key, verify_license_key, get_machine_fingerprint

def cli_keygen():
    parser = argparse.ArgumentParser(description="VyaparLedger Pro - Vendor Offline License Key Generator")
    parser.add_argument("--machine", "-m", required=True, help="Customer Machine ID (e.g. VYAP-ABCD-1234-EF56)")
    parser.add_argument("--company", "-c", required=True, help="Customer Company Name")
    parser.add_argument("--expiry", "-e", default="PERPETUAL", help="Expiry Date (YYYY-MM-DD or 'PERPETUAL')")
    
    args = parser.parse_args()
    
    key = generate_license_key(args.machine, args.company, args.expiry)
    print("\n" + "="*60)
    print("  VYAPARLEDGER PRO - LICENSE KEY ISSUANCE")
    print("="*60)
    print(f"  Customer Machine ID : {args.machine}")
    print(f"  Registered Company  : {args.company}")
    print(f"  Validity / Expiry   : {args.expiry}")
    print(f"  Generated Key       : {key}")
    print("="*60)
    
    # Self-test validation
    valid, msg, exp = verify_license_key(args.machine, args.company, key)
    if valid:
        print("  [SUCCESS] Verification passed: Key is cryptographically valid.\n")
    else:
        print(f"  [ERROR] Verification check failed: {msg}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli_keygen()
    else:
        print("\nInteractive Vendor License Key Generator:")
        print("-" * 45)
        curr_m = get_machine_fingerprint()
        print(f"Current PC Machine ID (for quick testing): {curr_m}\n")
        m_id = input(f"Enter Customer Machine ID [{curr_m}]: ").strip() or curr_m
        c_name = input("Enter Customer Company Name [e.g. Sita Ram & Sons]: ").strip() or "Sita Ram & Sons Traders"
        exp_in = input("Enter Expiry Date (YYYY-MM-DD) or press Enter for PERPETUAL: ").strip() or "PERPETUAL"
        
        key = generate_license_key(m_id, c_name, exp_in)
        print("\n" + "="*50)
        print(f"Generated Activation Key:\n>>> {key} <<<")
        print("="*50 + "\n")


import os
import sys
import time
from longport.openapi import QuoteContext, Config

def test_import_clash():
    print("--- [DIAG] Import Clash Test ---")
    from shared.config import settings
    
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    
    # 1. IMPORT RUST MODULE (But don't init class)
    print("[*] Importing l0_rust module...")
from l0_ingest import l0_rust
    print("[+] l0_rust module imported.")

    # 2. Initialize Python QuoteContext
    print("[*] Creating QuoteContext(config)...")
    try:
        ctx = QuoteContext(config)
        print("[+] QuoteContext created successfully.")
    except Exception as e:
        print(f"[-] QuoteContext creation failed: {e}")
        return

    print("[+] Test Complete.")

if __name__ == "__main__":
    test_import_clash()

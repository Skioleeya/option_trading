
import os
import sys
import time
from longport.openapi import QuoteContext, Config
import l0_rust

def test_dual_stack_clash():
    print("--- [DIAG] Dual-Stack Ingest Clash Test ---")
    from shared.config import settings
    
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    
    # 1. Initialize Python QuoteContext
    print("[*] Creating QuoteContext(config)...")
    try:
        ctx = QuoteContext(config)
        print("[+] QuoteContext created successfully.")
    except Exception as e:
        print(f"[-] QuoteContext creation failed: {e}")
        return

    # 2. Initialize Rust Gateway
    print("[*] Initializing l0_rust.RustIngestGateway()...")
    try:
        rust = l0_rust.RustIngestGateway()
        print("[+] Rust Gateway object created.")
    except Exception as e:
        print(f"[-] Rust initialization failed: {e}")
        return

    # 3. Start Rust Gateway
    print("[*] Starting Rust Gateway thread...")
    try:
        rust.start(["SPY.US"], "clash_test_shm", 1)
        print("[+] Rust Gateway started.")
    except Exception as e:
        print(f"[-] Rust Gateway start failed: {e}")

    # 4. Cleanup
    time.sleep(2)
    print("[*] Cleaning up...")
    rust.stop()
    print("[+] Test Complete.")

if __name__ == "__main__":
    test_dual_stack_clash()


import os
import sys
import time
from longport.openapi import QuoteContext, Config

def test_longport_direct():
    print("--- [DIAG] LongPort Connection Precise Check ---")
    from shared.config import settings
    
    ak = settings.longport_app_key
    sk = settings.longport_app_secret
    at = settings.longport_access_token

    def inspect(name, val):
        if not val:
            print(f"[-] {name} is EMPTY")
            return
        print(f"[*] {name}: len={len(val)}, repr={repr(val)}")
        # Check for control characters
        for c in val:
            if ord(c) < 32:
                print(f"    WARNING: Hidden control char found: ord={ord(c)}")

    inspect("APP_KEY", ak)
    inspect("SECRET", sk)
    inspect("TOKEN_START", at[:20] if at else None)
    
    config = Config(
        app_key=ak,
        app_secret=sk,
        access_token=at,
    )
    
    try:
        print("[*] Creating QuoteContext...")
        ctx = QuoteContext(config)
        print("[+] QuoteContext created successfully.")
        
        print("[*] Testing metadata fetch (SPY.US)...")
        quotes = ctx.quote(["SPY.US"])
        if quotes:
            print(f"[+] SUCCESS! SPY Last Done: {quotes[0].last_done}")
        else:
            print("[-] Metadata fetch returned empty.")
            
    except Exception as e:
        print(f"[-] LongPort connection failed: {e}")

if __name__ == "__main__":
    test_longport_direct()

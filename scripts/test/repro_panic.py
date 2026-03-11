
import os
import sys
import time
from l0_ingest import l0_rust

def repro():
    # Set RUST_BACKTRACE=1 in the environment
    os.environ["RUST_BACKTRACE"] = "1"
    
    print("--- [REPRO] Attempting to reproduce Rust Ingest Gateway panic ---")
    
    try:
        gateway = l0_rust.RustIngestGateway()
        print("[+] RustIngestGateway initialized.")
    except Exception as e:
        print(f"[-] Failed to initialize RustIngestGateway: {e}")
        return

    # Generate 360 dummy symbols
    # Standard format: SPY260305C00480000.US (roughly)
    symbols = [f"SPY260305C{400000 + i*500:08d}.US" for i in range(360)]
    shm_path = "sentinel_shm_repro"
    
    print(f"[*] Starting gateway with {len(symbols)} symbols on {shm_path}...")
    try:
        # This spawns a thread. We need to wait for it to panic.
        gateway.start(symbols, shm_path, 1)
        print("[+] gateway.start() called. Waiting for panic or data...")
    except Exception as e:
        print(f"[-] gateway.start() raised exception: {e}")
        return

    # Keep alive to see stdout/stderr from the Rust thread
    for i in range(10):
        print(f"[*] Monitoring... {i}s")
        time.sleep(1)
    
    print("[*] Repro script finished. Check if a panic message appeared above.")

if __name__ == "__main__":
    repro()

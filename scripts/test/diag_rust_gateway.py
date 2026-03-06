
import os
import sys
import time
import l0_rust
from l1_compute.rust_bridge import RustBridge

def test_rust_gateway_direct():
    print("--- [DIAG] Rust Ingest Gateway Standalone Test ---")
    
    # 1. Initialize Gateway
    try:
        gateway = l0_rust.RustIngestGateway()
        print("[+] RustIngestGateway initialized.")
    except Exception as e:
        print(f"[-] Failed to initialize RustIngestGateway: {e}")
        return

    shm_path = "test_shm_diag"
    symbols = ["SPY260306C680000.US", "SPY260306P680000.US"]
    
    # 2. Try to start
    print(f"[*] Starting gateway with {symbols} on {shm_path}...")
    try:
        # Note: start() usually returns immediately as it spawns a thread
        gateway.start(symbols, shm_path, 1)
        print("[+] Gateway.start() called successfully.")
    except Exception as e:
        print(f"[-] Gateway.start() failed: {e}")
        return

    # 3. Wait a bit for SHM creation
    print("[*] Waiting 3 seconds for SHM creation...")
    time.sleep(3)

    # 4. Try to connect via RustBridge
    bridge = RustBridge(shm_path)
    print(f"[*] Attempting to connect to {shm_path}...")
    connected = bridge.connect()
    
    if connected:
        print(f"[+] SUCCESS! Connected to SHM in {bridge.mm_path} namespace.")
        print(f"    SHM Stats: Head={bridge.head_ptr}, Tail={bridge.tail_ptr}")
        
        # 5. Poll for any data (unlikely if no real feed, but let's check)
        events = list(bridge.poll())
        print(f"[*] Polled events: {len(events)}")
        
        # Cleanup
        gateway.stop()
        print("[+] Gateway stopped.")
    else:
        print("[-] FAILURE! Could not connect to SHM.")
        # Check permissions or path
        print(f"    Last attempted path: {shm_path}")

if __name__ == "__main__":
    test_rust_gateway_direct()

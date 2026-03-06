import time
import l0_rust
import sys
import os

# Ensure the bridge is in the path
sys.path.append(os.path.join(os.getcwd(), "l1_compute"))
from rust_bridge import RustBridge

def test_gateway_ipc():
    # 1. Initialize Rust IngestGateway
    try:
        gateway = l0_rust.RustIngestGateway()
        print("[Test] RustIngestGateway initialized.")
    except Exception as e:
        print(f"[Test] Failed to initialize gateway: {e}")
        return

    shm_path = f"sentinel_shm_{int(time.time())}"
    symbols = ["AAPL.US"] # Example
    
    # 2. Start Gateway
    print(f"[Test] Starting gateway on {shm_path} for {symbols} (Pinned to Core 1)")
    try:
        gateway.start(symbols, shm_path, 1)
    except Exception as e:
        print(f"[Test] Failed to start gateway: {e}")
        # Note: Might fail if LONGPORT_APP_KEY etc. are not set
    
    # 3. Initialize Python Bridge
    bridge = RustBridge(shm_path)
    bridge.connect()
    
    print("[Test] Polling for events (Press Ctrl+C to stop)...")
    latencies = []
    try:
        start_time = time.time()
        while time.time() - start_time < 10: # Test for 10 seconds
            for event in bridge.poll():
                now_ns = time.time_ns()
                latency_us = (now_ns - event['arrival_mono_ns']) / 1000
                latencies.append(latency_us)
                print(f"[Event] {event['symbol']} | Type: {event['event_type']} | OFII: {event['impact_index']:.2f} | Latency: {latency_us:.2f}us")
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        gateway.stop()
        print("[Test] Gateway stopped.")
        if latencies:
            print(f"[Stats] Avg Latency: {sum(latencies)/len(latencies):.2f}us | Min: {min(latencies):.2f}us | Max: {max(latencies):.2f}us")

def run_stress_test():
    gateway = l0_rust.RustIngestGateway()
    shm_path = f"sentinel_stress_{int(time.time())}"
    
    # Pre-create SHM for stress test
    bridge = RustBridge(shm_path)
    # We need to create it from Rust first or use a dummy start
    gateway.start([], shm_path, None) 
    bridge.connect()
    
    count = 1_000_000
    print(f"[Stress] Pushing {count} events...")
    
    import threading
    def producer_thread():
        gateway.stress_test("STRESS.US", count, shm_path)
    
    t = threading.Thread(target=producer_thread)
    t.start()
    
    received = 0
    start_time = time.time()
    while received < count:
        for event in bridge.poll():
            received += 1
            if received % 100000 == 0:
                print(f"[Stress] Received {received} events...")
        if time.time() - start_time > 30: # Timeout
            print("[Stress] Timeout!")
            break
            
    end_time = time.time()
    duration = end_time - start_time
    print(f"[Stress] Received {received}/{count} events in {duration:.2f}s")
    print(f"[Stress] Throughput: {received/duration:.2f} events/sec")
    
    gateway.stop()

if __name__ == "__main__":
    if "--stress" in sys.argv:
        run_stress_test()
    else:
        test_gateway_ipc()

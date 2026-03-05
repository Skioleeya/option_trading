import os
import sys
import time
import numpy as np

sys.path.append(os.getcwd())

try:
    import rust_kernel
except ImportError:
    print("[!] Failed to import rust_kernel. Did you run maturin develop?")
    sys.exit(1)

def run_zero_copy_benchmark():
    print("[*] Starting Zero-Copy Memory Alignment Benchmark...")
    
    # 1. Define the strict 512-length memory layout (Matching Rust #[repr(C)])
    MAX_STRIKES = 512
    ITERATIONS = 10_000
    
    print(f"[*] Allocating {MAX_STRIKES}-length float32 arrays (NumPy -> PyO3 layout)...")
    
    # Pre-allocate contiguous memory blocks (float32 matching Rust f32)
    spots = np.full(MAX_STRIKES, 600.0, dtype=np.float32)
    strikes = np.linspace(400.0, 800.0, MAX_STRIKES, dtype=np.float32)
    ivs = np.full(MAX_STRIKES, 0.25, dtype=np.float32)
    is_call = np.tile([True, False], MAX_STRIKES // 2).astype(np.bool_)
    
    print("[*] Memory blocks allocated and aligned.")
    print(f"[*] Dispatching {ITERATIONS:,} iterations to Rust FFI boundary...")
    
    start_time = time.perf_counter()
    
    for _ in range(ITERATIONS):
        # We call the new Rust entry point 
        # Passing pointers/references directly to the pre-allocated numpy arrays
        res = rust_kernel.compute_from_arrays(spots, strikes, ivs, is_call)
        
    end_time = time.perf_counter()
    diff = max(end_time - start_time, 1e-9)
    
    total_ms = diff * 1000.0
    ops_per_sec = ITERATIONS / diff
    
    print("\n--- ZERO-COPY FFI BENCHMARK RESULTS ---")
    print(f"Total Time ({ITERATIONS:,} loops): {total_ms:.2f} ms")
    print(f"Throughput: {ops_per_sec:,.0f} ops/sec")
    print(f"Average FFI Overhead: {(total_ms / ITERATIONS) * 1000.0:.2f} microseconds per call")
    print("---------------------------------------")
    print("[*] Benchmark Complete.")

if __name__ == "__main__":
    run_zero_copy_benchmark()

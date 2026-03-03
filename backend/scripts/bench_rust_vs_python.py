import time
import math
import random

try:
    import ndm_rust
    print("ndm_rust successfully imported!")
except ImportError as e:
    print(f"Failed to import ndm_rust: {e}")
    exit(1)

def python_pearson(spots, ivs):
    n = len(spots)
    if n < 2 or n != len(ivs):
        return None
    
    sum_x = sum(spots)
    sum_y = sum(ivs)
    sum_x2 = sum(x * x for x in spots)
    sum_y2 = sum(y * y for y in ivs)
    sum_xy = sum(x * y for x, y in zip(spots, ivs))

    numerator = n * sum_xy - sum_x * sum_y
    denominator_x = n * sum_x2 - sum_x**2
    denominator_y = n * sum_y2 - sum_y**2

    if denominator_x <= 0 or denominator_y <= 0:
        return None

    return numerator / (math.sqrt(denominator_x) * math.sqrt(denominator_y))

N = 500
spots = [random.uniform(500, 600) for _ in range(N)]
ivs = [random.uniform(0.1, 0.3) for _ in range(N)]

# Correctness check
rust_r = ndm_rust.pearson_r(spots, ivs)
py_r = python_pearson(spots, ivs)
print(f"Rust Result:   {rust_r}")
print(f"Python Result: {py_r}")
assert abs(rust_r - py_r) < 1e-9, "Mismatch between Rust and Python!"

# Benchmark
RUNS = 10000

t0 = time.perf_counter()
for _ in range(RUNS):
    ndm_rust.pearson_r(spots, ivs)
t_rust = time.perf_counter() - t0

t0 = time.perf_counter()
for _ in range(RUNS):
    python_pearson(spots, ivs)
t_py = time.perf_counter() - t0

print("\n--- Benchmark (10,000 inner loops over 500-element array) ---")
print(f"Python time: {t_py:.3f}s")
print(f"Rust time:   {t_rust:.3f}s")
if t_rust > 0:
    print(f"Speedup:     {t_py/t_rust:.1f}x")

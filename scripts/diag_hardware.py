import sys
import os
import platform
import multiprocessing

try:
    import numpy as np
    print(f"NumPy Version: {np.__version__}")
except ImportError:
    print("NumPy not found")

try:
    import cupy as cp
    print(f"CuPy Version: {cp.__version__}")
    try:
        device_count = cp.cuda.runtime.getDeviceCount()
        print(f"CUDA Device Count: {device_count}")
        for i in range(device_count):
            props = cp.cuda.runtime.getDeviceProperties(i)
            print(f"  Device {i}: {props['name'].decode()} (CC {props['major']}.{props['minor']})")
        
        # Test a small kernel
        x = cp.zeros(1)
        print("GPU Warmup successful.")
    except Exception as e:
        print(f"CuPy found but CUDA error: {e}")
except ImportError:
    print("CuPy not found")

try:
    import numba
    print(f"Numba Version: {numba.__version__}")
    # Check if Numba can see CUDA
    from numba import cuda
    print(f"Numba CUDA detected: {cuda.is_available()}")
except ImportError:
    print("Numba not found")

print(f"CPU Count (logical): {multiprocessing.cpu_count()}")
print(f"Platform: {platform.platform()}")
print(f"Python Version: {sys.version}")

# Check environment variables related to threading
for env in ["OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"]:
    val = os.environ.get(env)
    if val:
        print(f"{env}: {val}")
    else:
        print(f"{env}: Not set (defaults to all cores)")

import psutil
import subprocess
import time

def check_resources():
    print("=" * 40)
    print("   System Resource Usage Monitor   ")
    print("=" * 40)
    
    # 1. CPU Usage
    # Take a 1-second sample to get an accurate reading
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"[CPU] Overall Load: {cpu_percent}%")
    if cpu_percent < 30:
        print("      Status: LOW LOAD (Expected for offloaded computation)")
    elif cpu_percent > 80:
        print("      Status: HIGH LOAD (Unexpected if fully offloading to GPU)")
    else:
        print("      Status: MODERATE LOAD")
        
    print("-" * 40)
        
    # 2. GPU Usage
    try:
        # Run nvidia-smi to get GPU utilization
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            text=True
        )
        lines = [line.strip() for line in output.strip().split('\n') if line.strip()]
        
        for line in lines:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 5:
                idx, name, util, mem_used, mem_total = parts
                gpu_percent = int(util)
                print(f"[GPU {idx}] Model: {name}")
                print(f"        Engine Load: {gpu_percent}%")
                print(f"        Memory Used: {mem_used} MiB / {mem_total} MiB")
                
                if gpu_percent > 70:
                    print("        Status: HIGH COMPUTATION LOAD (Expected)")
                elif gpu_percent < 10:
                    print("        Status: LOW LOAD (Potentially idle)")
                else:
                    print("        Status: MODERATE LOAD")
                print("-" * 40)
                
    except FileNotFoundError:
        print("[GPU] Error: nvidia-smi not found. Ensure NVIDIA drivers are installed.")
    except Exception as e:
        print(f"[GPU] Error checking GPU: {e}")

if __name__ == "__main__":
    check_resources()

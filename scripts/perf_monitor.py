import subprocess
import time
import psutil
import os
import json
from datetime import datetime

def get_gpu_metrics():
    try:
        cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,utilization.memory", "--format=csv,noheader,nounits"]
        output = subprocess.check_output(cmd).decode('utf-8').strip()
        gpu_util, mem_used, mem_util = output.split(', ')
        return {
            "gpu_util": float(gpu_util),
            "gpu_mem_used": float(mem_used),
            "gpu_mem_util": float(mem_util)
        }
    except Exception as e:
        return {"error": str(e)}

def monitor_system(duration=60, interval=1):
    print(f"[*] Starting 60s Monitoring Session at {datetime.now().isoformat()}")
    results = []
    
    # Identify target processes
    uvicorn_pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'uvicorn' in (proc.info['name'] or '').lower() or (proc.info['cmdline'] and 'uvicorn' in ' '.join(proc.info['cmdline'])):
                uvicorn_pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    print(f"[*] Identified Uvicorn PIDs: {uvicorn_pids}")
    
    start_time = time.time()
    while time.time() - start_time < duration:
        sample = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "gpu": get_gpu_metrics(),
            "process_stats": []
        }
        
        for pid in uvicorn_pids:
            try:
                p = psutil.Process(pid)
                sample["process_stats"].append({
                    "pid": pid,
                    "cpu_percent": p.cpu_percent(),
                    "mem_rss_mb": p.memory_info().rss / (1024 * 1024)
                })
            except:
                continue
                
        results.append(sample)
        time.sleep(interval)
        
    print(f"[*] Monitoring Complete. Captured {len(results)} samples.")
    return results

if __name__ == "__main__":
    data = monitor_system()
    output_path = r"e:\US.market\Option_v3\logs\perf_capture.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[!] Results saved to {output_path}")

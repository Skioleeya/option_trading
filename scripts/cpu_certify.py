import psutil
import time
import sys

def run_certification(duration=60, threshold=50.0):
    print(f"[*] Starting {duration}s CPU Certification Session...")
    print(f"[*] Target: Backend System CPU < {threshold}%")
    
    # Identify target processes
    targets = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = p.info['name'].lower() if p.info['name'] else ""
            cmd = " ".join(p.info['cmdline'] or []).lower()
            if 'python' in name or 'uvicorn' in name:
                if 'cpu_certify' not in cmd and 'perf_monitor' not in cmd:
                    targets.append(p)
                    # Initialize cpu_percent (first call returns 0, primes the tracker)
                    p.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not targets:
        print("[!] No backend processes found. Make sure Uvicorn is running.")
        sys.exit(1)
        
    print(f"[*] Found {len(targets)} backend processes: {[p.pid for p in targets]}")
    
    # Get system CPU count to calculate true system-wide utilization percentage
    # equivalent to Windows Task Manager
    sys_cores = psutil.cpu_count()
    
    start_time = time.time()
    samples = []
    breaches = 0
    
    print("\n--- BEGIN 60s CAPTURE ---")
    while time.time() - start_time < duration:
        time.sleep(1.0)
        total_cpu = 0.0
        active_pids = []
        for p in targets:
            try:
                # Get per-core % and normalize to system-wide %
                cpu_p = p.cpu_percent() / sys_cores
                total_cpu += cpu_p
                active_pids.append(p.pid)
            except psutil.NoSuchProcess:
                pass
                
        samples.append(total_cpu)
        status = "✅ PASSED" if total_cpu < threshold else "❌ FAILED"
        if total_cpu >= threshold:
            breaches += 1
            
        print(f"[{time.strftime('%H:%M:%S')}] Active PIDs: {len(active_pids)} | Total Backend CPU: {total_cpu:.1f}% | {status}")
    
    avg_cpu = sum(samples) / len(samples) if samples else 0
    max_cpu = max(samples) if samples else 0
    
    print("\n--- CERTIFICATION RESULTS ---")
    print(f"Duration:   {duration}s")
    print(f"Target:     < {threshold}%")
    print(f"Average CPU:{avg_cpu:.1f}%")
    print(f"Peak CPU:   {max_cpu:.1f}%")
    print(f"Breaches:   {breaches}")
    
    if breaches == 0:
        print("\n✅ CERTIFICATION PASSED: Backend CPU remained below 50% for 60s.")
    else:
        print("\n❌ CERTIFICATION FAILED: Backend CPU exceeded 50%.")

if __name__ == "__main__":
    run_certification()

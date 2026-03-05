import psutil
import time

def get_top_cpu():
    print(f"{'PID':<10} {'Name':<25} {'CPU %':<10} {'Memory (MB)':<15}")
    print("-" * 60)
    
    # Get all processes
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        processes.append(proc)
        
    # First call always returns 0, wait 1s
    time.sleep(1)
    
    top_procs = []
    for proc in processes:
        try:
            # Refresh cpu_percent
            cpu = proc.cpu_percent()
            mem = proc.memory_info().rss / (1024 * 1024)
            top_procs.append((proc.pid, proc.name(), cpu, mem))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    # Sort by CPU %
    top_procs.sort(key=lambda x: x[2], reverse=True)
    
    for pid, name, cpu, mem in top_procs[:15]:
        print(f"{pid:<10} {name:<25} {cpu:<10.1f} {mem:<15.1f}")

if __name__ == "__main__":
    get_top_cpu()

# pin_processes.ps1
# Institutional-Grade Optimization: Pin Python compute processes to isolated physical cores.
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\infra\pin_processes.ps1

$affinityMask = 0xF # Cores 0, 1, 2, 3

Write-Host "Searching for SPX Sentinel Python processes..." -ForegroundColor Cyan

$pyProcs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' AND CommandLine LIKE '%main.py%'" | ForEach-Object { Get-Process -Id $_.ProcessId }

if (-not $pyProcs) {
    Write-Host "No active SPX Sentinel Python processes found." -ForegroundColor Yellow
    exit
}

foreach ($proc in $pyProcs) {
    try {
        $proc.ProcessorAffinity = $affinityMask
        Write-Host "Successfully pinned PID $($proc.Id) to Affinity Mask: 0x$($affinityMask.ToString('X'))" -ForegroundColor Green
    } catch {
        Write-Host "ERROR pinning PID $($proc.Id): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "Optimization Complete." -ForegroundColor White

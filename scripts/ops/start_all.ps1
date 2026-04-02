param(
    [string]$BindHost = "0.0.0.0",
    [int]$RedisPort = 6380,
    [int]$BackendPort = 8001,
    [int]$FrontendPort = 5173,
    [int]$WaitTimeoutSec = 25,
    [string]$BackendLog = "logs/backend_runtime.current.log",
    [string]$FrontendLog = "logs/frontend_runtime.current.log",
    [switch]$NoDegradedRetry,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Output "[start-all] $Message"
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-ListeningPort {
    param([int]$Port)
    $conn = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -ne $conn
}

function Wait-ListeningPort {
    param(
        [int]$Port,
        [int]$TimeoutSec
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-ListeningPort -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return (Test-ListeningPort -Port $Port)
}

function Resolve-AbsPath {
    param(
        [string]$RepoRoot,
        [string]$PathOrRelative
    )
    if ([System.IO.Path]::IsPathRooted($PathOrRelative)) {
        return $PathOrRelative
    }
    return (Join-Path $RepoRoot $PathOrRelative)
}

function Start-RedisService {
    param(
        [string]$RepoRoot,
        [int]$Port,
        [int]$TimeoutSec
    )
    if (Test-ListeningPort -Port $Port) {
        Write-Step "Redis already listening at port $Port, skip start."
        return
    }

    $redisBat = Join-Path $RepoRoot "scripts/infra/redis-start.bat"
    if (-not (Test-Path $redisBat)) {
        throw "Redis start script not found: $redisBat"
    }

    Write-Step "Starting Redis via scripts/infra/redis-start.bat ..."
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "scripts\infra\redis-start.bat" -WorkingDirectory $RepoRoot -PassThru
    Write-Step "Redis launcher pid=$($proc.Id)"

    if (-not (Wait-ListeningPort -Port $Port -TimeoutSec $TimeoutSec)) {
        throw "Redis did not open port $Port within ${TimeoutSec}s."
    }
    Write-Step "Redis is listening on port $Port."
}

function Start-BackendService {
    param(
        [string]$RepoRoot,
        [string]$BindHost,
        [int]$Port,
        [int]$TimeoutSec,
        [string]$LogFile,
        [switch]$DisableRetry
    )
    $backendScript = Join-Path $RepoRoot "scripts/ops/start_backend.ps1"
    if (-not (Test-Path $backendScript)) {
        throw "Backend start script not found: $backendScript"
    }

    Write-Step "Starting backend in strict mode ..."
    & $backendScript -BindHost $BindHost -Port $Port -LogFile $LogFile

    if (Wait-ListeningPort -Port $Port -TimeoutSec $TimeoutSec) {
        Write-Step "Backend is listening on port $Port (strict)."
        return
    }

    if ($DisableRetry) {
        throw "Backend strict mode failed and degraded retry is disabled."
    }

    Write-Step "Strict mode did not become ready in ${TimeoutSec}s, retrying with -Degraded ..."
    & $backendScript -BindHost $BindHost -Port $Port -LogFile $LogFile -Degraded

    if (-not (Wait-ListeningPort -Port $Port -TimeoutSec $TimeoutSec)) {
        $logPath = Resolve-AbsPath -RepoRoot $RepoRoot -PathOrRelative $LogFile
        if (Test-Path $logPath) {
            Write-Step "Backend log tail:"
            Get-Content -Path $logPath -Tail 40
        }
        throw "Backend failed in strict and degraded mode (port $Port not listening)."
    }

    Write-Step "Backend is listening on port $Port (degraded)."
}

function Start-FrontendService {
    param(
        [string]$RepoRoot,
        [int]$Port,
        [int]$TimeoutSec,
        [string]$LogFile
    )
    if (Test-ListeningPort -Port $Port) {
        Write-Step "Frontend already listening at port $Port, skip start."
        return
    }

    $uiDir = Join-Path $RepoRoot "l4_ui"
    if (-not (Test-Path $uiDir)) {
        throw "Frontend directory not found: $uiDir"
    }

    $frontendLogPath = Resolve-AbsPath -RepoRoot $RepoRoot -PathOrRelative $LogFile
    $frontendLogDir = Split-Path -Parent $frontendLogPath
    New-Item -ItemType Directory -Path $frontendLogDir -Force | Out-Null

    $viteProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "vite" -or $_.CommandLine -match "npm run dev" }
    foreach ($p in $viteProcs) {
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        } catch {
            # Best effort cleanup.
        }
    }

    $cmd = "cd /d `"$uiDir`" && npm run dev -- --host 0.0.0.0 --port $Port >> `"$frontendLogPath`" 2>&1"
    Write-Step "Starting frontend via npm run dev ..."
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmd -WorkingDirectory $RepoRoot -PassThru
    Write-Step "Frontend launcher pid=$($proc.Id)"

    if (-not (Wait-ListeningPort -Port $Port -TimeoutSec $TimeoutSec)) {
        if (Test-Path $frontendLogPath) {
            Write-Step "Frontend log tail:"
            Get-Content -Path $frontendLogPath -Tail 40
        }
        throw "Frontend did not open port $Port within ${TimeoutSec}s."
    }
    Write-Step "Frontend is listening on port $Port."
}

function Verify-Stack {
    param(
        [int]$RedisPort,
        [int]$BackendPort,
        [int]$FrontendPort
    )
    $targets = @(
        @{ Name = "Redis"; Port = $RedisPort },
        @{ Name = "Backend"; Port = $BackendPort },
        @{ Name = "Frontend"; Port = $FrontendPort }
    )

    $rows = @()
    foreach ($t in $targets) {
        $conn = Get-NetTCPConnection -State Listen -LocalPort $t.Port -ErrorAction SilentlyContinue | Select-Object -First 1
        $rows += [pscustomobject]@{
            Service      = $t.Name
            Port         = $t.Port
            Listening    = [bool]($null -ne $conn)
            LocalAddress = if ($conn) { $conn.LocalAddress } else { "-" }
            PID          = if ($conn) { $conn.OwningProcess } else { "-" }
        }
    }

    Write-Output ""
    Write-Output "[start-all] Verification summary:"
    $rows | Format-Table -AutoSize

    $failed = $rows | Where-Object { -not $_.Listening }
    if ($failed) {
        throw "Verification failed: one or more services are not listening."
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $repoRoot

if (-not (Test-IsAdmin)) {
    Write-Warning "[start-all] Not running as Administrator. External-elevated host run is recommended."
}

if ($VerifyOnly) {
    Write-Step "VerifyOnly=true; skip startup and run verification only."
    Verify-Stack -RedisPort $RedisPort -BackendPort $BackendPort -FrontendPort $FrontendPort
    exit 0
}

Write-Step "RepoRoot=$repoRoot"
Write-Step "Startup order: Redis -> Backend(strict, fallback degraded) -> Frontend"

Start-RedisService -RepoRoot $repoRoot -Port $RedisPort -TimeoutSec $WaitTimeoutSec
Start-BackendService -RepoRoot $repoRoot -BindHost $BindHost -Port $BackendPort -TimeoutSec $WaitTimeoutSec -LogFile $BackendLog -DisableRetry:$NoDegradedRetry
Start-FrontendService -RepoRoot $repoRoot -Port $FrontendPort -TimeoutSec $WaitTimeoutSec -LogFile $FrontendLog

Verify-Stack -RedisPort $RedisPort -BackendPort $BackendPort -FrontendPort $FrontendPort

Write-Output ""
Write-Step "All services are up."
Write-Step "Frontend: http://localhost:$FrontendPort"
Write-Step "Backend:  http://localhost:$BackendPort"

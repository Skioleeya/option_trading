param(
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8001,
    [switch]$Degraded,
    [switch]$HotfixActiveOptions,
    [int]$HotfixMinVolume = 10,
    [string]$LogFile = "logs/backend_runtime.current.log",
    [switch]$Foreground,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Output "[backend-start] Scanning for existing backend processes..."
$procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "uvicorn" -and $_.CommandLine -match "main:app" }
if ($procs) {
    foreach ($p in $procs) {
        Write-Output "[backend-start] Stopping existing backend PID: $($p.ProcessId)"
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $repoRoot

if ([System.IO.Path]::IsPathRooted($LogFile)) {
    $logPath = $LogFile
} else {
    $logPath = Join-Path $repoRoot $LogFile
}

$logDir = Split-Path -Parent $logPath
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

if ($Degraded) {
    throw "Degraded startup mode is forbidden. Use strict startup only."
}

$bootMode = "strict"
$envCmd = "set PYTHONPATH=."
if ($HotfixActiveOptions) {
    $hotfixVolume = [Math]::Max(1, [int]$HotfixMinVolume)
    $bootMode = "strict+active-options-hotfix"
    $envCmd = "$envCmd&& set FLOW_ACTIVE_MIN_VOLUME=$hotfixVolume"
}

$uvicornCmd = "python -m uvicorn main:app --host $BindHost --port $Port"
$redirectCmd = ">> `"$logPath`" 2>&1"
$cmd = "$envCmd&& $uvicornCmd $redirectCmd"

if ($DryRun) {
    Write-Output "[backend-start] DryRun=true"
    Write-Output "[backend-start] mode=$bootMode"
    Write-Output "[backend-start] hotfix_active_options=$HotfixActiveOptions"
    if ($HotfixActiveOptions) {
        Write-Output "[backend-start] flow_active_min_volume=$hotfixVolume"
    }
    Write-Output "[backend-start] foreground=$Foreground"
    Write-Output "[backend-start] log=$logPath"
    Write-Output "[backend-start] cmd=cmd.exe /c $cmd"
    exit 0
}

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logPath -Encoding utf8 -Value "[$stamp] [BOOT] mode=$bootMode host=$BindHost port=$Port"

if ($Foreground) {
    $env:PYTHONPATH = "."
    if ($HotfixActiveOptions) {
        $env:FLOW_ACTIVE_MIN_VOLUME = [string]$hotfixVolume
    }
    Write-Output "[backend-start] foreground=true mode=$bootMode log=$logPath"
    Write-Output "[backend-start] hotfix_active_options=$HotfixActiveOptions"
    if ($HotfixActiveOptions) {
        Write-Output "[backend-start] flow_active_min_volume=$hotfixVolume"
    }
    Write-Output "[backend-start] running=python -m uvicorn main:app --host $BindHost --port $Port"
    # Foreground path must run under cmd to avoid PowerShell NativeCommandError on uvicorn stderr logs.
    cmd.exe /c "$envCmd&& $uvicornCmd 2>&1" | Tee-Object -FilePath $logPath -Append
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        exit $exitCode
    }
} else {
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmd -WorkingDirectory $repoRoot -PassThru
    Write-Output "[backend-start] started pid=$($proc.Id) mode=$bootMode log=$logPath"
}

param(
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8001,
    [switch]$Degraded,
    [string]$LogFile = "logs/backend_runtime.current.log",
    [switch]$Foreground,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $repoRoot

if ([System.IO.Path]::IsPathRooted($LogFile)) {
    $logPath = $LogFile
} else {
    $logPath = Join-Path $repoRoot $LogFile
}

$logDir = Split-Path -Parent $logPath
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$bootMode = "strict"
$envCmd = "set PYTHONPATH=."
if ($Degraded) {
    $bootMode = "degraded"
    $envCmd = "$envCmd&& set LONGPORT_STARTUP_STRICT_CONNECTIVITY=false&& set LONGBRIDGE_STARTUP_STRICT_CONNECTIVITY=false"
}

$uvicornCmd = "python -m uvicorn main:app --host $BindHost --port $Port"
$redirectCmd = ">> `"$logPath`" 2>&1"
$cmd = "$envCmd&& $uvicornCmd $redirectCmd"

if ($DryRun) {
    Write-Output "[backend-start] DryRun=true"
    Write-Output "[backend-start] mode=$bootMode"
    Write-Output "[backend-start] foreground=$Foreground"
    Write-Output "[backend-start] log=$logPath"
    Write-Output "[backend-start] cmd=cmd.exe /c $cmd"
    exit 0
}

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logPath -Encoding utf8 -Value "[$stamp] [BOOT] mode=$bootMode host=$BindHost port=$Port"

if ($Foreground) {
    $env:PYTHONPATH = "."
    if ($Degraded) {
        $env:LONGPORT_STARTUP_STRICT_CONNECTIVITY = "false"
        $env:LONGBRIDGE_STARTUP_STRICT_CONNECTIVITY = "false"
    }
    Write-Output "[backend-start] foreground=true mode=$bootMode log=$logPath"
    Write-Output "[backend-start] running=python -m uvicorn main:app --host $BindHost --port $Port"
    & python -m uvicorn main:app --host $BindHost --port $Port 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} else {
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmd -WorkingDirectory $repoRoot -PassThru
    Write-Output "[backend-start] started pid=$($proc.Id) mode=$bootMode log=$logPath"
}

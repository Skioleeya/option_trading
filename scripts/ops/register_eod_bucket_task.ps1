param(
    [string]$PythonExe = "python",
    [string]$RepoRoot = "",
    [string]$ConfigPath = "scripts/diagnostics/config/eod_bucket_thresholds.json",
    [string]$DataRoot = "data",
    [string]$OutRoot = "data/cold",
    [string]$TaskPrefix = "EODBucket",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$scriptPath = Join-Path $RepoRoot "scripts/diagnostics/eod_bucket_archive.py"
if (-not (Test-Path $scriptPath)) {
    throw "Script not found: $scriptPath"
}
$runnerPath = Join-Path $RepoRoot "scripts/ops/run_eod_bucket.ps1"
if (-not (Test-Path $runnerPath)) {
    throw "Runner not found: $runnerPath"
}

$primaryTask = "${TaskPrefix}Primary"
$retryTask = "${TaskPrefix}Retry"

$runCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runnerPath`""

$primaryCreate = "schtasks /Create /F /TN `"$primaryTask`" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 16:01 /TR `"$runCmd`""
$retryCreate = "schtasks /Create /F /TN `"$retryTask`" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 17:00 /TR `"$runCmd`""

Write-Host "[EODBucketTask] Preview commands:"
Write-Host $primaryCreate
Write-Host $retryCreate
Write-Host ""
Write-Host "[EODBucketTask] Query commands:"
Write-Host "schtasks /Query /TN `"$primaryTask`" /V /FO LIST"
Write-Host "schtasks /Query /TN `"$retryTask`" /V /FO LIST"

if ($Apply) {
    Write-Host ""
    Write-Host "[EODBucketTask] Applying scheduled tasks..."
    cmd /c $primaryCreate | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Failed creating task: $primaryTask (exit=$LASTEXITCODE)"
    }
    cmd /c $retryCreate | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Failed creating task: $retryTask (exit=$LASTEXITCODE)"
    }
    Write-Host "[EODBucketTask] Applied."
}

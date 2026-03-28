param(
    [string]$PythonExe = "python",
    [string]$RepoRoot = "",
    [string]$Date = "",
    [string]$ConfigPath = "scripts/diagnostics/config/eod_bucket_thresholds.json",
    [string]$DataRoot = "data",
    [string]$OutRoot = "data/cold",
    [string]$RunLabel = "manual",
    [double]$SettleStableWindowSeconds = 300,
    [double]$SettleTimeoutSeconds = 2400,
    [double]$SettlePollSeconds = 15,
    [int]$MaxAttempts = 2
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$waitScript = Join-Path $RepoRoot "scripts/diagnostics/wait_for_eod_sources_settle.py"
$verifyScript = Join-Path $RepoRoot "scripts/diagnostics/check_eod_manifest_sync.py"
if (-not (Test-Path $waitScript)) {
    throw "Settle guard script not found: $waitScript"
}
if (-not (Test-Path $verifyScript)) {
    throw "Manifest sync script not found: $verifyScript"
}

Set-Location $RepoRoot
if ([string]::IsNullOrWhiteSpace($Date)) {
    $Date = (& $PythonExe "-c" "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d'))").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Date)) {
        throw "Failed to determine ET trade date for EOD bucket run."
    }
}

$finalExit = 1
for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    Write-Host "[EODBucketRunner][$RunLabel] attempt=$attempt date=$Date settle_guard=start"
    & $PythonExe $waitScript --date $Date --root $DataRoot --stable-window-seconds $SettleStableWindowSeconds --timeout-seconds $SettleTimeoutSeconds --poll-seconds $SettlePollSeconds
    $settleExit = $LASTEXITCODE
    if ($settleExit -ne 0) {
        Write-Host "[EODBucketRunner][$RunLabel] attempt=$attempt settle_guard=failed exit=$settleExit"
        exit $settleExit
    }

    Write-Host "[EODBucketRunner][$RunLabel] attempt=$attempt archive=start"
    & $PythonExe "scripts/diagnostics/eod_bucket_archive.py" --date $Date --config $ConfigPath --root $DataRoot --out-root $OutRoot --strict-quality
    $archiveExit = $LASTEXITCODE
    Write-Host "[EODBucketRunner][$RunLabel] attempt=$attempt archive=done exit=$archiveExit"

    Write-Host "[EODBucketRunner][$RunLabel] attempt=$attempt sync_check=start"
    & $PythonExe $verifyScript --date $Date --out-root $OutRoot
    $syncExit = $LASTEXITCODE
    Write-Host "[EODBucketRunner][$RunLabel] attempt=$attempt sync_check=done exit=$syncExit"

    if ($syncExit -eq 0 -and ($archiveExit -eq 0 -or $archiveExit -eq 2)) {
        exit $archiveExit
    }

    $finalExit = if ($archiveExit -ne 0) { $archiveExit } else { $syncExit }
    Write-Warning "[EODBucketRunner][$RunLabel] attempt=$attempt incomplete (archive_exit=$archiveExit sync_exit=$syncExit); retrying if attempts remain."
}

exit $finalExit

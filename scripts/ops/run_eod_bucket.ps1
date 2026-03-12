param(
    [string]$PythonExe = "python",
    [string]$RepoRoot = "",
    [string]$ConfigPath = "scripts/diagnostics/config/eod_bucket_thresholds.json",
    [string]$DataRoot = "data",
    [string]$OutRoot = "data/cold"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

Set-Location $RepoRoot
& $PythonExe "scripts/diagnostics/eod_bucket_archive.py" --config $ConfigPath --root $DataRoot --out-root $OutRoot --strict-quality
exit $LASTEXITCODE

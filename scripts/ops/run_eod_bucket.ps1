param(
    [string]$ConfigPath = "scripts/diagnostics/config/eod_bucket_thresholds.json",
    [string]$DataRoot = "data",
    [string]$OutRoot = "data/cold",
    [double]$SettleStableWindowSeconds = 30,
    [double]$SettleTimeoutSeconds = 900,
    [double]$SettlePollSeconds = 5,
    [int]$MaxAttempts = 2,
    [string]$RunLabel = "Manual"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-TaskLog {
    param([string]$Message)
    Write-Host "[EODBucketTaskWin] $Message"
}

function Resolve-RepositoryRoot {
    param([string]$ScriptPath)

    $scriptDir = Split-Path -Parent $ScriptPath
    $repoCandidate = Join-Path $scriptDir "..\.."
    return (Resolve-Path -Path $repoCandidate).Path
}

function Resolve-RepositoryPython {
    param([string]$RepositoryRoot)

    $pythonExe = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
        throw "repo virtualenv python not found: $pythonExe"
    }
    return (Resolve-Path -LiteralPath $pythonExe).Path
}

try {
    $repoRoot = Resolve-RepositoryRoot -ScriptPath $PSCommandPath
    Set-Location -Path $repoRoot
    Write-TaskLog "repo_root=$repoRoot"

    $pythonExe = Resolve-RepositoryPython -RepositoryRoot $repoRoot
    Write-TaskLog "python=$pythonExe"

    $args = @(
        "manage.py",
        "run-eod-bucket",
        "--python-exe", $pythonExe,
        "--repo-root", $repoRoot,
        "--config-path", $ConfigPath,
        "--data-root", $DataRoot,
        "--out-root", $OutRoot,
        "--run-label", $RunLabel,
        "--settle-stable-window-seconds", $SettleStableWindowSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture),
        "--settle-timeout-seconds", $SettleTimeoutSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture),
        "--settle-poll-seconds", $SettlePollSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture),
        "--max-attempts", $MaxAttempts.ToString([System.Globalization.CultureInfo]::InvariantCulture)
    )

    Write-TaskLog "exec=$pythonExe $($args -join ' ')"
    & $pythonExe @args
    $exitCode = $LASTEXITCODE
    Write-TaskLog "exit_code=$exitCode"
    exit $exitCode
}
catch {
    Write-Error "[EODBucketTaskWin] fatal=$($_.Exception.Message)"
    exit 1
}

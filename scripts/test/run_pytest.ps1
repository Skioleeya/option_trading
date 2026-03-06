param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (Test-IsAdmin) {
    throw "Refusing to run pytest in Administrator context. Use a normal user shell to avoid mixed-permission cache artifacts."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $repoRoot

$cacheDir = "tmp/pytest_cache"
New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null

$args = @("-m", "pytest", "-o", "cache_dir=$cacheDir")
if ($PytestArgs) {
    $args += $PytestArgs
}

Write-Host "[pytest-wrapper] cache_dir=$cacheDir"
Write-Host "[pytest-wrapper] context=non-admin"
python @args

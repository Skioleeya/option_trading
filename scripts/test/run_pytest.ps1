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

# Ensure Windows expanduser() can resolve a home directory in constrained shells.
if (-not $env:USERPROFILE -and $env:HOME) {
    $env:USERPROFILE = $env:HOME
}
if ($env:USERPROFILE) {
    if (-not $env:HOMEDRIVE -and $env:USERPROFILE.Length -ge 2) {
        $env:HOMEDRIVE = $env:USERPROFILE.Substring(0, 2)
    }
    if (-not $env:HOMEPATH -and $env:USERPROFILE.Length -ge 3) {
        $env:HOMEPATH = $env:USERPROFILE.Substring(2)
    }
}

# Ensure critical Windows environment variables exist so Winsock providers
# (for example %SystemRoot%\system32\mswsock.dll) can be resolved correctly.
if (-not $env:SystemRoot) {
    $env:SystemRoot = "C:\Windows"
}
if (-not $env:windir) {
    $env:windir = $env:SystemRoot
}

# Avoid loading unrelated global pytest entrypoint plugins from host environment.
if (-not $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD) {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
}

$args = @("-m", "pytest", "-p", "pytest_asyncio.plugin", "-o", "cache_dir=$cacheDir")
if ($PytestArgs) {
    $args += $PytestArgs
}

Write-Host "[pytest-wrapper] cache_dir=$cacheDir"
Write-Host "[pytest-wrapper] context=non-admin"
python @args
exit $LASTEXITCODE

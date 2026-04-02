param(
    [string]$CacheDir = "tmp/pytest_cache"
)

$ErrorActionPreference = "Stop"

function Test-DirectoryWriteAccess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $probePath = Join-Path $Path (".pytest-acl-probe-" + [guid]::NewGuid().ToString("N"))
    try {
        Set-Content -LiteralPath $probePath -Value "probe" -NoNewline
        Remove-Item -LiteralPath $probePath -Force
        return $true
    } catch {
        return $false
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $repoRoot

$resolvedCacheDir = Join-Path $repoRoot $CacheDir
if (-not (Test-Path -LiteralPath $resolvedCacheDir)) {
    New-Item -ItemType Directory -Path $resolvedCacheDir -Force | Out-Null
}

$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name

Write-Host "[pytest-cache-acl] target=$resolvedCacheDir"
Write-Host "[pytest-cache-acl] identity=$currentIdentity"

& takeown.exe /F $resolvedCacheDir /R /D Y | Out-Host
& icacls.exe $resolvedCacheDir /inheritance:r /grant:r "${currentIdentity}:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" "NT AUTHORITY\SYSTEM:(OI)(CI)F" /T /C | Out-Host

if (-not (Test-DirectoryWriteAccess -Path $resolvedCacheDir)) {
    $owner = (Get-Acl $resolvedCacheDir).Owner
    throw "ACL repair did not restore write access for '$currentIdentity' on '$resolvedCacheDir' (owner: '$owner')."
}

Write-Host "[pytest-cache-acl] write_probe=passed"

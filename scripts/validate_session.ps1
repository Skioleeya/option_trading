param(
    [string]$SessionPath = ""
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    $script:HasError = $true
}

function Pass {
    param([string]$Message)
    Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Read-ActiveSessionPath {
    param([string]$ContextProjectFile)
    if (-not (Test-Path $ContextProjectFile)) {
        throw "Context project file not found: $ContextProjectFile"
    }
    $line = Select-String -Path $ContextProjectFile -Pattern '^- Path:\s+`?(.+?)/project_state\.md`?$' | Select-Object -First 1
    if (-not $line) {
        throw "Cannot parse active session path from $ContextProjectFile"
    }
    $rel = $line.Matches[0].Groups[1].Value
    return $rel
}

function Require-Key {
    param(
        [string]$Text,
        [string]$KeyPattern,
        [string]$Label
    )
    $m = [regex]::Match($Text, $KeyPattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if (-not $m.Success) {
        Fail "meta.yaml missing or empty: $Label"
    } else {
        Pass "meta.yaml has $Label"
    }
}

$script:HasError = $false
$repoRoot = Get-RepoRoot
Set-Location $repoRoot

$contextProject = Join-Path $repoRoot "notes/context/project_state.md"
$contextTasks = Join-Path $repoRoot "notes/context/open_tasks.md"
$contextHandoff = Join-Path $repoRoot "notes/context/handoff.md"

if ([string]::IsNullOrWhiteSpace($SessionPath)) {
    $SessionPath = Read-ActiveSessionPath -ContextProjectFile $contextProject
}
$activeSessionPath = Read-ActiveSessionPath -ContextProjectFile $contextProject

$sessionDir = Join-Path $repoRoot $SessionPath
if (-not (Test-Path $sessionDir)) {
    throw "Session directory not found: $SessionPath"
}

Write-Host "Validating session: $SessionPath"

$requiredFiles = @(
    "project_state.md",
    "open_tasks.md",
    "handoff.md",
    "meta.yaml"
)

foreach ($f in $requiredFiles) {
    $p = Join-Path $sessionDir $f
    if (Test-Path $p) { Pass "$f exists" } else { Fail "$f missing" }
}

$metaPath = Join-Path $sessionDir "meta.yaml"
if (Test-Path $metaPath) {
    $meta = Get-Content $metaPath -Raw
    Require-Key -Text $meta -KeyPattern '^session_id:\s*".+?"\s*$' -Label "session_id"
    Require-Key -Text $meta -KeyPattern '^branch:\s*".+?"\s*$' -Label "branch"
    Require-Key -Text $meta -KeyPattern '^base_commit:\s*".+?"\s*$' -Label "base_commit"
    Require-Key -Text $meta -KeyPattern '^head_commit:\s*".+?"\s*$' -Label "head_commit"
    Require-Key -Text $meta -KeyPattern '^tests_passed:\s*.*$' -Label "tests_passed"
}

if ($SessionPath -eq $activeSessionPath) {
    $expectedProjectPtrA = '- Path: ' + $SessionPath + '/project_state.md'
    $expectedProjectPtrB = '- Path: `' + $SessionPath + '/project_state.md`'
    $expectedTasksPtrA = '- Path: ' + $SessionPath + '/open_tasks.md'
    $expectedTasksPtrB = '- Path: `' + $SessionPath + '/open_tasks.md`'
    $expectedHandoffPtrA = '- Path: ' + $SessionPath + '/handoff.md'
    $expectedHandoffPtrB = '- Path: `' + $SessionPath + '/handoff.md`'
    $expectedMetaPtrA = '- Meta: ' + $SessionPath + '/meta.yaml'
    $expectedMetaPtrB = '- Meta: `' + $SessionPath + '/meta.yaml`'

    $projectText = Get-Content $contextProject -Raw
    $tasksText = Get-Content $contextTasks -Raw
    $handoffText = Get-Content $contextHandoff -Raw

    if (($projectText -match [regex]::Escape($expectedProjectPtrA)) -or ($projectText -match [regex]::Escape($expectedProjectPtrB))) { Pass "project_state index pointer OK" } else { Fail "project_state index pointer mismatch" }
    if (($projectText -match [regex]::Escape($expectedMetaPtrA)) -or ($projectText -match [regex]::Escape($expectedMetaPtrB))) { Pass "project_state meta pointer OK" } else { Fail "project_state meta pointer mismatch" }
    if (($tasksText -match [regex]::Escape($expectedTasksPtrA)) -or ($tasksText -match [regex]::Escape($expectedTasksPtrB))) { Pass "open_tasks index pointer OK" } else { Fail "open_tasks index pointer mismatch" }
    if (($handoffText -match [regex]::Escape($expectedHandoffPtrA)) -or ($handoffText -match [regex]::Escape($expectedHandoffPtrB))) { Pass "handoff index pointer OK" } else { Fail "handoff index pointer mismatch" }
    if (($handoffText -match [regex]::Escape($expectedMetaPtrA)) -or ($handoffText -match [regex]::Escape($expectedMetaPtrB))) { Pass "handoff meta pointer OK" } else { Fail "handoff meta pointer mismatch" }
} else {
    Pass "Pointer checks skipped (validating non-active session)"
}

if ($script:HasError) {
    Write-Host "Session validation failed." -ForegroundColor Red
    exit 1
}

Write-Host "Session validation passed." -ForegroundColor Green
exit 0

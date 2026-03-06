param(
    [Parameter(Mandatory = $true)]
    [string]$TaskId,
    [string]$Title = "",
    [string]$Scope = "hotfix + modularization",
    [string]$Owner = "Codex",
    [string]$ParentSession = "",
    [switch]$UseTimeBucket,
    [switch]$NoPointerUpdate
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    return $root
}

function Ensure-Template {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Template not found: $Path"
    }
}

function Get-RecentSessionLines {
    param([string]$ContextProjectPath)
    if (-not (Test-Path $ContextProjectPath)) {
        return @()
    }
    $raw = Get-Content $ContextProjectPath -Raw
    $matches = [regex]::Matches($raw, '^- (?:`)?notes/sessions/.+(?:`)?$', [System.Text.RegularExpressions.RegexOptions]::Multiline)
    $lines = @()
    foreach ($m in $matches) { $lines += $m.Value.Trim() }
    return $lines
}

function Get-GlobalBacklogLines {
    param([string]$ContextTasksPath)
    if (-not (Test-Path $ContextTasksPath)) {
        return @('- [ ] P0:', '- [ ] P1:', '- [ ] P2:')
    }
    $raw = Get-Content $ContextTasksPath -Raw
    $m = [regex]::Match(
        $raw,
        '(?s)## Global Backlog \(Cross-Session\)\s*\r?\n(?<body>.*?)\r?\n## Process'
    )
    if (-not $m.Success) {
        return @('- [ ] P0:', '- [ ] P1:', '- [ ] P2:')
    }
    $body = $m.Groups['body'].Value.Trim()
    if ([string]::IsNullOrWhiteSpace($body)) {
        return @('- [ ] P0:', '- [ ] P1:', '- [ ] P2:')
    }
    return ($body -split '\r?\n')
}

$repoRoot = Get-RepoRoot
Set-Location $repoRoot

$date = Get-Date -Format "yyyy-MM-dd"
$hhmm = Get-Date -Format "HHmm"
$timeStampEt = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"

$sessionsRoot = Join-Path $repoRoot "notes/sessions"
$templatesRoot = Join-Path $sessionsRoot "_templates"
$sessionRel = if ($UseTimeBucket) {
    "notes/sessions/$date/$hhmm/$TaskId"
} else {
    "notes/sessions/$date/$TaskId"
}
$sessionDir = Join-Path $repoRoot $sessionRel

$projectTemplate = Join-Path $templatesRoot "project_state.template.md"
$tasksTemplate = Join-Path $templatesRoot "open_tasks.template.md"
$handoffTemplate = Join-Path $templatesRoot "handoff.template.md"
$metaTemplate = Join-Path $templatesRoot "meta.template.yaml"

Ensure-Template $projectTemplate
Ensure-Template $tasksTemplate
Ensure-Template $handoffTemplate
Ensure-Template $metaTemplate

if (Test-Path $sessionDir) {
    throw "Session already exists: $sessionRel"
}

New-Item -ItemType Directory -Path $sessionDir -Force | Out-Null
Copy-Item $projectTemplate (Join-Path $sessionDir "project_state.md")
Copy-Item $tasksTemplate (Join-Path $sessionDir "open_tasks.md")
Copy-Item $handoffTemplate (Join-Path $sessionDir "handoff.md")
Copy-Item $metaTemplate (Join-Path $sessionDir "meta.yaml")

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
$commit = (git rev-parse --short HEAD).Trim()

if ([string]::IsNullOrWhiteSpace($Title)) {
    $Title = $TaskId.Replace("_", " ")
}

$metaPath = Join-Path $sessionDir "meta.yaml"
$meta = Get-Content $metaPath -Raw
$sessionId = if ($UseTimeBucket) { "$date/$hhmm/$TaskId" } else { "$date/$TaskId" }
$meta = $meta -replace 'session_id: "YYYY-MM-DD/HHMM_scope_hotfix_or_mod"', "session_id: `"$sessionId`""
$meta = $meta -replace 'title: ""', "title: `"$Title`""
$meta = $meta -replace 'scope: "hotfix only \| hotfix \+ modularization \| feature"', "scope: `"$Scope`""
$meta = $meta -replace 'owner: ""', "owner: `"$Owner`""
$meta = $meta -replace 'started_at_et: ""', "started_at_et: `"$timeStampEt`""
$meta = $meta -replace 'updated_at_et: ""', "updated_at_et: `"$timeStampEt`""
$meta = $meta -replace 'branch: ""', "branch: `"$branch`""
$meta = $meta -replace 'base_commit: ""', "base_commit: `"$commit`""
$meta = $meta -replace 'head_commit: ""', "head_commit: `"$commit`""
if (-not [string]::IsNullOrWhiteSpace($ParentSession)) {
    $meta = $meta -replace 'parent_session: null', "parent_session: `"$ParentSession`""
}
Set-Content -Path $metaPath -Value $meta -Encoding UTF8

$contextProjectPath = Join-Path $repoRoot "notes/context/project_state.md"
$contextTasksPath = Join-Path $repoRoot "notes/context/open_tasks.md"
$contextHandoffPath = Join-Path $repoRoot "notes/context/handoff.md"

if (-not $NoPointerUpdate) {
    $currentRecent = "- $sessionRel/"
    $recent = @($currentRecent)
    foreach ($line in (Get-RecentSessionLines -ContextProjectPath $contextProjectPath)) {
        if ($line -ne $currentRecent) { $recent += $line }
    }
    $recent = $recent | Select-Object -Unique | Select-Object -First 5
    $recentText = ($recent -join [Environment]::NewLine)

    $backlogLines = Get-GlobalBacklogLines -ContextTasksPath $contextTasksPath
    $backlogText = ($backlogLines -join [Environment]::NewLine)

    $projectIndex = @"
# Project State (Index)

## Active Session
- Path: $sessionRel/project_state.md
- Meta: $sessionRel/meta.yaml
- Status: ACTIVE

## Recent Sessions
$recentText

## Global Rules
- Session folders are immutable records; do not overwrite prior sessions.
- New substantive work must create a new session folder under notes/sessions/YYYY-MM-DD/<task-id>/ (or notes/sessions/YYYY-MM-DD/HHMM/<task-id>/ with time-bucket mode).
- Keep this index file updated with the latest active session pointer.
"@

    $tasksIndex = @"
# Open Tasks (Index)

## Active Session Tasks
- Path: $sessionRel/open_tasks.md

## Global Backlog (Cross-Session)
$backlogText

## Process
- Task details and completion evidence belong in the session-local open_tasks.md.
- Keep this file as the long-horizon queue and session pointer only.
"@

    $handoffIndex = @"
# Handoff (Index)

## Active Handoff
- Path: $sessionRel/handoff.md
- Meta: $sessionRel/meta.yaml

## Latest Outcome
- Session: $date/$TaskId
- Summary: Session created. Fill handoff.md when work is completed.

## Next Session Bootstrap
1. Read this file.
2. Read notes/context/project_state.md and notes/context/open_tasks.md.
3. Open the active session folder and continue from its handoff.md.
"@

    Set-Content -Path $contextProjectPath -Value $projectIndex -Encoding UTF8
    Set-Content -Path $contextTasksPath -Value $tasksIndex -Encoding UTF8
    Set-Content -Path $contextHandoffPath -Value $handoffIndex -Encoding UTF8
}

Write-Host "Session created: $sessionRel"
if ($NoPointerUpdate) {
    Write-Host "Context pointer update: skipped (-NoPointerUpdate)"
} else {
    Write-Host "Updated context pointers:"
    Write-Host " - notes/context/project_state.md"
    Write-Host " - notes/context/open_tasks.md"
    Write-Host " - notes/context/handoff.md"
}

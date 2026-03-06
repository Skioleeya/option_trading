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

function Get-MetaQuotedListItems {
    param(
        [string]$MetaText,
        [string]$Key
    )
    $pattern = '(?ms)^' + [regex]::Escape($Key) + ':\s*\r?\n(?<body>(?:\s*-\s*".*?"\s*\r?\n)*)'
    $m = [regex]::Match($MetaText, $pattern)
    if (-not $m.Success) {
        return @()
    }

    $items = @()
    $lines = $m.Groups['body'].Value -split '\r?\n'
    foreach ($line in $lines) {
        $t = $line.Trim()
        if ($t -match '^\-\s*"(?<v>.*)"\s*$') {
            $items += $Matches['v']
        }
    }
    return $items
}

function Get-UncheckedOpenTaskItems {
    param(
        [string]$OpenTasksPath
    )
    $rows = @()
    if (-not (Test-Path $OpenTasksPath)) {
        return $rows
    }

    $section = ""
    $lineNo = 0
    foreach ($line in Get-Content $OpenTasksPath) {
        $lineNo += 1
        if ($line -match '^\s*##\s+(?<sec>.+?)\s*$') {
            $section = $Matches['sec'].Trim()
            continue
        }
        if ($line -match '^\s*-\s*\[\s\]\s*(?<item>.+?)\s*$') {
            $item = $Matches['item'].Trim()
            # Explicit superseded markers are treated as closed records.
            if ($item -match '(?i)SUP(?:ER|SER)SEDED-BY\s*:') {
                continue
            }
            $rows += [pscustomobject]@{
                section = $section
                item = $item
                line = $lineNo
            }
        }
    }

    return $rows
}

function Get-HandoffDebtField {
    param(
        [string]$HandoffText,
        [string]$FieldName
    )
    $pattern = '(?im)^\s*(?:-\s*)?' + [regex]::Escape($FieldName) + '\s*:\s*(.+?)\s*$'
    $m = [regex]::Match($HandoffText, $pattern)
    if (-not $m.Success) {
        return $null
    }
    return $m.Groups[1].Value.Trim()
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

# SOP sync gate (AGENTS.md §7)
$metaText = Get-Content $metaPath -Raw
$changedFiles = @(Get-MetaQuotedListItems -MetaText $metaText -Key "files_changed")
$runtimeRegex = '^(l0_ingest|l1_compute|l2_decision|l3_assembly|l4_ui|app)/'
$runtimeChanged = @(
    $changedFiles | Where-Object {
        $_ -match $runtimeRegex -and
        $_ -notmatch '/tests?/' -and
        $_ -notmatch '^docs/' -and
        $_ -notmatch '^notes/'
    }
)
$sopChanged = @($changedFiles | Where-Object { $_ -match '^docs/SOP/' })
$handoffPath = Join-Path $sessionDir "handoff.md"
$handoffText = if (Test-Path $handoffPath) { Get-Content $handoffPath -Raw } else { "" }
$hasSopExempt = [regex]::IsMatch($handoffText, '(?im)^\s*SOP-EXEMPT\s*:\s*.+$')

if ($runtimeChanged.Count -gt 0) {
    if ($sopChanged.Count -gt 0) {
        Pass "SOP sync gate OK (docs/SOP updated)"
    } elseif ($hasSopExempt) {
        Pass "SOP sync gate OK (SOP-EXEMPT present in handoff.md)"
    } else {
        Fail "SOP sync gate failed: runtime files changed but no docs/SOP update and no SOP-EXEMPT in handoff.md"
    }
} else {
    Pass "SOP sync gate skipped (no runtime-layer files changed)"
}

# Technical debt gate (AGENTS.md §8)
if ($SessionPath -eq $activeSessionPath) {
    $openTasksPath = Join-Path $sessionDir "open_tasks.md"
    $uncheckedItems = @(Get-UncheckedOpenTaskItems -OpenTasksPath $openTasksPath)

    $debtExempt = Get-HandoffDebtField -HandoffText $handoffText -FieldName "DEBT-EXEMPT"
    $debtOwner = Get-HandoffDebtField -HandoffText $handoffText -FieldName "DEBT-OWNER"
    $debtDueRaw = Get-HandoffDebtField -HandoffText $handoffText -FieldName "DEBT-DUE"
    $debtRisk = Get-HandoffDebtField -HandoffText $handoffText -FieldName "DEBT-RISK"
    $debtNewRaw = Get-HandoffDebtField -HandoffText $handoffText -FieldName "DEBT-NEW"
    $debtClosedRaw = Get-HandoffDebtField -HandoffText $handoffText -FieldName "DEBT-CLOSED"
    $debtDeltaRaw = Get-HandoffDebtField -HandoffText $handoffText -FieldName "DEBT-DELTA"
    $debtJustification = Get-HandoffDebtField -HandoffText $handoffText -FieldName "DEBT-JUSTIFICATION"

    # 8.2: unchecked tasks require complete DEBT-EXEMPT record.
    if ($uncheckedItems.Count -gt 0) {
        if ([string]::IsNullOrWhiteSpace($debtExempt)) { Fail "Debt gate: unchecked tasks exist but DEBT-EXEMPT missing" } else { Pass "Debt gate: DEBT-EXEMPT present" }
        if ([string]::IsNullOrWhiteSpace($debtOwner)) { Fail "Debt gate: DEBT-OWNER missing" } else { Pass "Debt gate: DEBT-OWNER present" }
        if ([string]::IsNullOrWhiteSpace($debtDueRaw)) { Fail "Debt gate: DEBT-DUE missing" } else { Pass "Debt gate: DEBT-DUE present" }
        if ([string]::IsNullOrWhiteSpace($debtRisk)) { Fail "Debt gate: DEBT-RISK missing" } else { Pass "Debt gate: DEBT-RISK present" }
    } else {
        Pass "Debt gate: no unchecked tasks"
    }

    # 8.6: debt metrics are always mandatory on active handoff.
    if ([string]::IsNullOrWhiteSpace($debtNewRaw)) { Fail "Debt gate: DEBT-NEW missing" } else { Pass "Debt gate: DEBT-NEW present" }
    if ([string]::IsNullOrWhiteSpace($debtClosedRaw)) { Fail "Debt gate: DEBT-CLOSED missing" } else { Pass "Debt gate: DEBT-CLOSED present" }
    if ([string]::IsNullOrWhiteSpace($debtDeltaRaw)) { Fail "Debt gate: DEBT-DELTA missing" } else { Pass "Debt gate: DEBT-DELTA present" }

    $debtNew = 0
    $debtClosed = 0
    $debtDelta = 0
    $metricsParsable = $true
    if (-not [int]::TryParse(($debtNewRaw ?? ""), [ref]$debtNew)) {
        Fail "Debt gate: DEBT-NEW must be integer"
        $metricsParsable = $false
    }
    if (-not [int]::TryParse(($debtClosedRaw ?? ""), [ref]$debtClosed)) {
        Fail "Debt gate: DEBT-CLOSED must be integer"
        $metricsParsable = $false
    }
    if (-not [int]::TryParse(($debtDeltaRaw ?? ""), [ref]$debtDelta)) {
        Fail "Debt gate: DEBT-DELTA must be integer"
        $metricsParsable = $false
    }
    if ($metricsParsable) {
        if ($debtDelta -ne ($debtNew - $debtClosed)) {
            Fail "Debt gate: DEBT-DELTA must equal DEBT-NEW - DEBT-CLOSED"
        } else {
            Pass "Debt gate: DEBT metrics arithmetic OK"
        }
        if ($debtDelta -gt 0) {
            if ([string]::IsNullOrWhiteSpace($debtJustification)) {
                Fail "Debt gate: DEBT-DELTA > 0 requires DEBT-JUSTIFICATION"
            } else {
                Pass "Debt gate: DEBT-JUSTIFICATION present"
            }
        }
    }

    # 8.3: due date SLA checks for deferred debt
    if ($uncheckedItems.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($debtDueRaw)) {
        $due = [datetime]::MinValue
        if (-not [datetime]::TryParseExact($debtDueRaw, "yyyy-MM-dd", $null, [System.Globalization.DateTimeStyles]::None, [ref]$due)) {
            Fail "Debt gate: DEBT-DUE must be YYYY-MM-DD"
        } else {
            $today = (Get-Date).Date
            $dueDate = $due.Date
            if ($dueDate -lt $today) {
                Fail "Debt gate: DEBT-DUE is overdue"
            }

            $hasP0 = ($uncheckedItems | Where-Object { $_.item -match '^\s*P0\s*:' }).Count -gt 0
            $hasP1 = ($uncheckedItems | Where-Object { $_.item -match '^\s*P1\s*:' }).Count -gt 0
            $maxDays = 5
            if ($hasP0) {
                $maxDays = 0
            } elseif ($hasP1) {
                $maxDays = 2
            }
            $maxDue = $today.AddDays($maxDays)
            if ($dueDate -gt $maxDue) {
                Fail "Debt gate: DEBT-DUE exceeds SLA window for active priority"
            } else {
                Pass "Debt gate: DEBT-DUE within SLA window"
            }
        }
    }

    # 8.5: duplicate unresolved debt records across sessions must be superseded.
    $allOpenTasks = Get-ChildItem -Path (Join-Path $repoRoot "notes/sessions") -Recurse -Filter open_tasks.md
    $allDebtItems = @()
    foreach ($ot in $allOpenTasks) {
        $rows = Get-UncheckedOpenTaskItems -OpenTasksPath $ot.FullName
        foreach ($r in $rows) {
            $allDebtItems += ($r.item.Trim().ToLowerInvariant())
        }
    }
    $dupDebt = @($allDebtItems | Group-Object | Where-Object { $_.Count -gt 1 })
    if ($dupDebt.Count -gt 0) {
        Fail "Debt gate: duplicate unresolved debt entries found across sessions without supersede marker"
    } else {
        Pass "Debt gate: no duplicate unresolved debt entries"
    }
} else {
    Pass "Debt gate skipped (validating non-active session)"
}

if ($script:HasError) {
    Write-Host "Session validation failed." -ForegroundColor Red
    exit 1
}

Write-Host "Session validation passed." -ForegroundColor Green
exit 0

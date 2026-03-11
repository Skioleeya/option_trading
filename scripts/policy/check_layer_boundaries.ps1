param(
    [string]$PolicyPath = "scripts/policy/layer_boundary_rules.json"
)

$ErrorActionPreference = "Stop"

function Normalize-RepoPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ""
    }
    $v = $Path.Replace('\\', '/').Trim()
    if ($v.StartsWith("./")) {
        $v = $v.Substring(2)
    }
    return $v
}

function Test-PathGlobMatch {
    param(
        [string]$Path,
        [string]$Glob
    )
    $normPath = Normalize-RepoPath -Path $Path
    $normGlob = Normalize-RepoPath -Path $Glob
    if ([string]::IsNullOrWhiteSpace($normPath) -or [string]::IsNullOrWhiteSpace($normGlob)) {
        return $false
    }
    return $normPath -like $normGlob
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $repoRoot

if (-not (Test-Path $PolicyPath)) {
    Write-Host "[FAIL] Missing policy file: $PolicyPath" -ForegroundColor Red
    exit 1
}

try {
    $policy = Get-Content $PolicyPath -Raw | ConvertFrom-Json
} catch {
    Write-Host "[FAIL] Cannot parse policy file: $PolicyPath" -ForegroundColor Red
    exit 1
}

$rules = @($policy.rules | Where-Object { $_.enabled -ne $false })
$allowRules = @($policy.allow)

$tracked = @(git ls-files)
$targets = @(
    $tracked | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_) -and
        (Normalize-RepoPath -Path $_) -match '\.(py|ts|tsx)$' -and
        (Test-Path (Join-Path $repoRoot $_))
    }
)

$hits = @()
foreach ($target in $targets) {
    $normTarget = Normalize-RepoPath -Path $target
    $fullPath = Join-Path $repoRoot $normTarget

    $lineNo = 0
    foreach ($line in Get-Content $fullPath) {
        $lineNo += 1

        foreach ($rule in $rules) {
            $ruleGlob = [string]$rule.glob
            $ruleRegex = [string]$rule.regex
            if ([string]::IsNullOrWhiteSpace($ruleGlob) -or [string]::IsNullOrWhiteSpace($ruleRegex)) {
                continue
            }
            if (-not (Test-PathGlobMatch -Path $normTarget -Glob $ruleGlob)) {
                continue
            }
            if (-not [regex]::IsMatch($line, $ruleRegex, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
                continue
            }

            $allowed = $false
            foreach ($allowRule in $allowRules) {
                $allowGlob = [string]$allowRule.glob
                $allowRegex = [string]$allowRule.regex
                if ([string]::IsNullOrWhiteSpace($allowGlob) -or [string]::IsNullOrWhiteSpace($allowRegex)) {
                    continue
                }
                if ((Test-PathGlobMatch -Path $normTarget -Glob $allowGlob) -and
                    [regex]::IsMatch($line, $allowRegex, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
                    $allowed = $true
                    break
                }
            }

            if (-not $allowed) {
                $hits += [pscustomobject]@{
                    id = [string]$rule.id
                    path = $normTarget
                    line = $lineNo
                    message = [string]$rule.message
                    excerpt = $line.Trim()
                }
            }
        }
    }
}

if ($hits.Count -gt 0) {
    Write-Host ("[FAIL] Layer boundary violations: " + $hits.Count) -ForegroundColor Red
    foreach ($hit in $hits) {
        $msg = if ([string]::IsNullOrWhiteSpace($hit.message)) { "Layer boundary violation" } else { $hit.message }
        Write-Host ("[FAIL] {0}:{1} [{2}] {3} | {4}" -f $hit.path, $hit.line, $hit.id, $msg, $hit.excerpt) -ForegroundColor Red
    }
    exit 1
}

Write-Host "[OK] Layer boundary scan passed (full repository)" -ForegroundColor Green
exit 0

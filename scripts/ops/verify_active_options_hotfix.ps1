param(
    [string]$ApiBase = "http://127.0.0.1:8001",
    [int]$TimeoutSec = 5
)

$ErrorActionPreference = "Stop"

function Invoke-JsonGet {
    param(
        [string]$Url,
        [int]$TimeoutSec
    )
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
    return ($resp.Content | ConvertFrom-Json)
}

function Resolve-ChainSize {
    param([object]$DebugJson)
    $stores = $DebugJson.stores
    if ($null -eq $stores) {
        return 0
    }
    if ($stores.PSObject.Properties.Name -contains "store") {
        $inner = $stores.store
        if ($null -ne $inner -and $inner.PSObject.Properties.Name -contains "chain_size") {
            return [int]$inner.chain_size
        }
    }
    if ($stores.PSObject.Properties.Name -contains "chain_size") {
        return [int]$stores.chain_size
    }
    return 0
}

function Resolve-IntField {
    param(
        [object]$Obj,
        [string]$FieldName
    )
    if ($null -eq $Obj) {
        return 0
    }
    if ($Obj.PSObject.Properties.Name -contains $FieldName) {
        return [int]$Obj.$FieldName
    }
    return 0
}

$healthUrl = "$($ApiBase.TrimEnd('/'))/health"
$debugUrl = "$($ApiBase.TrimEnd('/'))/debug/persistence_status"

Write-Output "[verify-hotfix] health_url=$healthUrl"
try {
    $healthResp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec $TimeoutSec
} catch {
    Write-Error "[verify-hotfix] health request failed: $($_.Exception.Message)"
    exit 1
}

if ($healthResp.StatusCode -ne 200) {
    Write-Error "[verify-hotfix] health status is not 200: $($healthResp.StatusCode)"
    exit 1
}
Write-Output "[verify-hotfix] health_status=200"

$debugJson = Invoke-JsonGet -Url $debugUrl -TimeoutSec $TimeoutSec
$chainSize = Resolve-ChainSize -DebugJson $debugJson
$activeDiag = $debugJson.active_options
if ($null -eq $activeDiag) {
    Write-Error "[verify-hotfix] missing active_options diagnostics in /debug/persistence_status response."
    exit 1
}

$totalRows = Resolve-IntField -Obj $activeDiag -FieldName "rows_total"
$placeholderRows = Resolve-IntField -Obj $activeDiag -FieldName "rows_placeholder"
$realRows = Resolve-IntField -Obj $activeDiag -FieldName "rows_real"
$liveRows = Resolve-IntField -Obj $activeDiag -FieldName "live_rows"
$degradedRows = Resolve-IntField -Obj $activeDiag -FieldName "degraded_rows"
$missingGammaRows = Resolve-IntField -Obj $activeDiag -FieldName "missing_gamma_rows"
$missingTurnoverRows = Resolve-IntField -Obj $activeDiag -FieldName "missing_turnover_rows"

Write-Output "[verify-hotfix] chain_size=$chainSize active_options_total=$totalRows placeholder=$placeholderRows real=$realRows"
Write-Output "[verify-hotfix] live_rows=$liveRows degraded_rows=$degradedRows missing_gamma_rows=$missingGammaRows missing_turnover_rows=$missingTurnoverRows"

if ($chainSize -gt 0 -and $liveRows -lt 1) {
    Write-Warning "[verify-hotfix] chain has data but live_rows=0 (can be expected in degraded/after-hours scenarios)."
}

if ($chainSize -gt 0 -and $realRows -lt 1) {
    Write-Error "[verify-hotfix] chain has data but active_options has no real rows according to diagnostics."
    exit 1
}

if ($chainSize -gt 0 -and $totalRows -lt 1) {
    Write-Error "[verify-hotfix] chain has data but active_options diagnostics report zero rows."
    exit 1
}

if ($chainSize -gt 0 -and $realRows -gt 0 -and $missingTurnoverRows -ge $realRows) {
    Write-Error "[verify-hotfix] all real rows are missing turnover; turnover hotfix regression suspected."
    exit 1
}

Write-Output "[verify-hotfix] PASS"
exit 0

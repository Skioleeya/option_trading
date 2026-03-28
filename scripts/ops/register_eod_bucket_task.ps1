param(
    [string]$PythonExe = "python",
    [string]$RepoRoot = "",
    [string]$ConfigPath = "scripts/diagnostics/config/eod_bucket_thresholds.json",
    [string]$DataRoot = "data",
    [string]$OutRoot = "data/cold",
    [string]$TaskPrefix = "EODBucket",
    [double]$SettleStableWindowSeconds = 30,
    [double]$SettleTimeoutSeconds = 900,
    [double]$SettlePollSeconds = 5,
    [int]$MaxAttempts = 2,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$scriptPath = Join-Path $RepoRoot "scripts/diagnostics/eod_bucket_archive.py"
if (-not (Test-Path $scriptPath)) {
    throw "Script not found: $scriptPath"
}
$runnerPath = Join-Path $RepoRoot "scripts/ops/run_eod_bucket.ps1"
if (-not (Test-Path $runnerPath)) {
    throw "Runner not found: $runnerPath"
}

$primaryTask = "${TaskPrefix}Primary"
$retryTask = "${TaskPrefix}Retry"

$sharedArgs = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $runnerPath,
    "-ConfigPath",
    $ConfigPath,
    "-DataRoot",
    $DataRoot,
    "-OutRoot",
    $OutRoot,
    "-SettleStableWindowSeconds",
    "$SettleStableWindowSeconds",
    "-SettleTimeoutSeconds",
    "$SettleTimeoutSeconds",
    "-SettlePollSeconds",
    "$SettlePollSeconds",
    "-MaxAttempts",
    "$MaxAttempts"
)

$primaryArgs = @($sharedArgs + @("-RunLabel", "Primary"))
$retryArgs = @($sharedArgs + @("-RunLabel", "Retry"))
$primaryArgText = [string]::Join(" ", @($primaryArgs | ForEach-Object {
    if ($_ -match '\s') { '"{0}"' -f $_ } else { "$_" }
}))
$retryArgText = [string]::Join(" ", @($retryArgs | ForEach-Object {
    if ($_ -match '\s') { '"{0}"' -f $_ } else { "$_" }
}))
$primaryAction = New-ScheduledTaskAction -Execute "powershell" -Argument $primaryArgText
$retryAction = New-ScheduledTaskAction -Execute "powershell" -Argument $retryArgText
$weekDays = @("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
$primaryTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $weekDays -At "4:01 PM"
$retryTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $weekDays -At "4:04 PM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew

Write-Host "[EODBucketTask] Preview commands:"
Write-Host ("TaskName={0} Trigger=16:01 StartWhenAvailable=True Execute={1} Arguments={2}" -f $primaryTask, $primaryAction.Execute, $primaryAction.Arguments)
Write-Host ("TaskName={0} Trigger=16:04 StartWhenAvailable=True Execute={1} Arguments={2}" -f $retryTask, $retryAction.Execute, $retryAction.Arguments)
Write-Host ""
Write-Host "[EODBucketTask] Query commands:"
Write-Host "Get-ScheduledTask -TaskName `"$primaryTask`" | Format-List TaskName,State,Actions,Triggers"
Write-Host "Get-ScheduledTask -TaskName `"$retryTask`" | Format-List TaskName,State,Actions,Triggers"

if ($Apply) {
    Write-Host ""
    Write-Host "[EODBucketTask] Applying scheduled tasks..."
    Register-ScheduledTask -TaskName $primaryTask -Action $primaryAction -Trigger $primaryTrigger -Settings $settings -Force | Out-Null
    Register-ScheduledTask -TaskName $retryTask -Action $retryAction -Trigger $retryTrigger -Settings $settings -Force | Out-Null
    Write-Host "[EODBucketTask] Applied."
}

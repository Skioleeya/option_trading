# Project State

## Snapshot
- DateTime (ET): 2026-07-10 16:11:23 -04:00
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `643a55e`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: fix the scheduled post-market EOD classifier failure.
- Scope In: Windows EOD task wrapper, EOD task guard regression, manual EOD verification.
- Scope Out: EOD classification thresholds, day-type policy, L0-L4 runtime behavior.

## What Changed (Latest Session)
- Files:
- `scripts/ops/run_eod_bucket.ps1`
- `scripts/test/test_eod_task_guards.py`
- Behavior:
- Root cause: scheduled `EODBucketPrimary`/`EODBucketRetry` used `Get-Command python`, resolving to `C:\Python314\python.exe`; that environment lacked `pyarrow`, causing archive and sync to fail.
- The Windows wrapper now hard-resolves `E:\US.market\Option_v4\.venv\Scripts\python.exe` and passes the same absolute venv Python through `--python-exe`.
- No compatibility fallback to PATH/system Python remains.
- Verification:
- Reproduced wrapper failure before fix: `ModuleNotFoundError: No module named 'pyarrow'`.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\ops\run_eod_bucket.ps1 ... -OutRoot tmp/eod_task_wrapper_fixed_20260710` -> PASS.
- `.\.venv\Scripts\python.exe manage.py run-pytest scripts\test\test_eod_task_guards.py` -> `7 passed`.
- Formal EOD bucket publish for `20260710` succeeded to `data/cold`, with `primary_day_type=balance_day`, `context_modifiers=[vol_crush]`, `quality=PASS`.

## Risks / Constraints
- Risk 1: Existing scheduled tasks already point to `scripts\ops\run_eod_bucket.ps1`, so script fix is sufficient; no task reinstall was required.
- Risk 2: `data/cold/20260710` artifacts were generated as operational EOD output and are intentionally not listed as code/session changed files.

## Next Action
- Immediate Next Step: run strict validation.
- Owner: Codex

# Project State

## Snapshot
- DateTime (ET): 2026-04-19 17:50:00 -04:00
- Branch: `main`
- Last Commit: `a23cf79`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `N/A`
  - L0-L4 Pipeline: `N/A`

## Current Focus
- Primary Goal: Restore missing Windows EOD task entry script for `EODBucketPrimary/EODBucketRetry`.
- Scope In: `scripts/ops/run_eod_bucket.ps1` recovery, deterministic repo-root set, explicit exit-code propagation, session evidence.
- Scope Out: L0-L4 runtime compute/decision changes, strategy behavior changes.

## What Changed (Latest Session)
- Files:
  - `scripts/ops/run_eod_bucket.ps1`
  - `notes/sessions/2026-04-19/restore-windows-eod-entry-20260419/*`
  - `notes/context/*` pointers
- Behavior:
  - Windows entry script now resolves repo root from script location, switches working directory, and delegates to `manage.py run-eod-bucket`.
  - Child process exit code is propagated to scheduler.
  - Script was copied to `/mnt/e/US.market/Option_v3/scripts/ops/` for host path alignment.
- Verification:
  - EOD guard tests passed (`6 passed`).
  - Windows probe confirmed script loads and command wiring is correct.
  - `python3 manage.py validate-session --strict` passed.

## Risks / Constraints
- Risk 1: Weekend/non-session execution returns non-zero by design due XNYS date gate.
- Risk 2: Linux environment lacks `pwsh`; host-side PowerShell validation requires `powershell.exe` probe.

## Next Action
- Immediate Next Step: Run strict validation and keep this session as active pointer.
- Owner: Codex

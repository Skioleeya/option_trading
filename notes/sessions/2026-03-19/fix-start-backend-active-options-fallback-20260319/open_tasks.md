# Open Tasks

## Priority Queue
- [x] P0: Foreground backend startup path switched to `cmd /c` wrapper to avoid PowerShell `NativeCommandError`.
  - Owner: Codex
  - Definition of Done: `start_backend.ps1 -Foreground` no longer runs `& python` directly and foreground command is cmd-wrapped.
  - Blocking: None
- [x] P1: ActiveOptions fallback now normalizes alias fields and emits hard fallback candidates when chain is non-empty.
  - Owner: Codex
  - Definition of Done: Empty min-volume filter no longer forces 5 placeholders when chain has rows but `turnover/open_interest` are unavailable.
  - Blocking: None
- [x] P1: ActiveOptions regression tests updated and passing.
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q` is green with alias/hard-fallback coverage.
  - Blocking: None
- [ ] P1: User-host live verification for `ActiveOptions real>=1` after hotfix restart.
  - Owner: User/Codex
  - Definition of Done: `scripts/ops/verify_active_options_hotfix.ps1` reports `chain_size>0` and `real>=1`.
  - Blocking: Local shell network stack instability (`WinError 10106`) may impact online verification.

## Parking Lot
- [ ] Evaluate time-of-day dynamic min-volume threshold after live validation baseline is stable.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Item (DateTime ET)

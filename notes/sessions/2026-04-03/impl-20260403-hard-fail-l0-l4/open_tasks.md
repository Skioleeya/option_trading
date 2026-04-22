# Open Tasks

## Priority Queue
- [x] P0: Enforce strict-only backend startup (no degraded entry/retry)
  - Owner: Codex
  - Definition of Done: `start_backend` rejects `-Degraded`; `start_all` no longer retries degraded mode.
  - Blocking: none
- [x] P1: Convert L0-L4 penetration test to hard-fail assertions
  - Owner: Codex
  - Definition of Done: connection/payload contract failures raise pytest failure; no silent pass path remains.
  - Blocking: none
- [x] P2: Harden intraday audit + SOP sync to strict-only policy
  - Owner: Codex
  - Definition of Done: audit outputs PASS/FAIL only and SOP startup contract reflects hard-fail mode.
  - Blocking: none

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Blocked degraded startup mode in `scripts/ops/start_backend.ps1` (2026-04-03 11:03 ET)
- [x] Removed degraded retry path from `scripts/ops/start_all.ps1` (2026-04-03 11:04 ET)
- [x] Locked `_startup_connectivity_probe()` to strict-only fail-fast (2026-04-03 11:04 ET)
- [x] Rewrote `scripts/test/test_l0_l4_pipeline.py` to assert-fail contract checks (2026-04-03 11:06 ET)
- [x] Hardened `scripts/diag/audit_intraday_core_flow.py` to strict PASS/FAIL checks (2026-04-03 11:07 ET)
- [x] Verified negative-path hard-fail and targeted app diagnostics tests (2026-04-03 11:08 ET)
- [x] Executed strict backend startup run and captured Arrow IPC mapping failure evidence from runtime logs (2026-04-03 11:20 ET)
- [x] Executed strict penetration test run (`test_l0_l4_pipeline`) and captured contract failure (`governor_telemetry` missing) (2026-04-03 11:20 ET)
- [x] Executed strict flow audit (`audit_intraday_core_flow --json`) and captured `overall=FAIL` with subsystem evidence (2026-04-03 11:20 ET)

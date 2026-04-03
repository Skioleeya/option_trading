# Project State

## Snapshot
- DateTime (ET): 2026-04-03 15:58:45 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `d35aa24`
- Environment:
  - Market: `OPEN`
  - Backend Startup (strict): `PASS`
  - L0-L4 Runtime: `PASS`

## Current Focus
- Primary Goal: Root-cause hard-cut remediation with TDD:
  - remove flow compatibility modules,
  - remove ActiveOptions fallback paths,
  - enforce Arrow startup gate with no retry fallback.
- Scope In:
  - `l2_decision/signals/flow/*` compatibility module retirement.
  - `shared/services/active_options_runtime.py` strict no-fallback/halt semantics.
  - `shared/services/l0_runtime/services/runtime/builder.py` startup gate and hard-fail semantics.
  - `shared/services/l0_runtime/services/subscription/__init__.py` writer-ready readiness contract.
  - L3/L4 active-options contract cleanup (`fallback_reason` / `is_synthetic_fallback` removal).
  - SOP sync + strict validation + backend restart/log verification.

## What Changed (Latest Session)
- Runtime Behavior:
  - Deleted `l2_decision/signals/flow` compatibility module tree (hard-cut import surface).
  - ActiveOptions runtime switched to strict no-fallback:
    - no synthetic/placeholder fallback emission,
    - hard-fail on empty filtered candidates / empty engine output / invalid input,
    - halted diagnostics contract added.
  - Housekeeping loop no longer degrades invalid ActiveOptions input; it hard-fails.
  - L0 Arrow startup now gates on writer-ready subscription with timeout (`longport_subscription_ready_timeout_sec`, default 60s).
  - Arrow consumer loop no longer retries attach fallback after startup gate failure.
- Contract Changes:
  - Removed row fields: `fallback_reason`, `is_synthetic_fallback`.
  - Removed fallback diagnostics fields from ActiveOptions runtime payload.
- Test/Guard Changes:
  - Added strict tests:
    - `scripts/test/test_active_options_strict_no_fallback.py`
    - `scripts/test/test_active_options_contract_no_fallback_fields.py`
    - `scripts/test/test_l0_arrow_startup_gate.py`
  - Extended `scripts/test/test_module_structure_guards.py` with flow-compat deletion guard.
- SOP Sync:
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `docs/SOP/L4_FRONTEND.md`

## Verification
- Targeted pytest suites: PASS.
- Strict session validation: PASS (`scripts/validate_session.ps1 -Strict`).
- Real-host backend restart: PASS.
- First 100 startup log lines from `logs/backend_runtime.postfix.log`: no Arrow mapping error storm; startup and subscription progression normal.

## Risks / Constraints
- Existing unrelated dirty-worktree files remain; this session did not revert or normalize unrelated changes.
- Session uses `OPENSPEC-EXEMPT` (runtime hardening within existing contract family, no new product surface).

## Next Action
- Keep monitoring runtime for `writer_not_ready_timeout` events in strict startup mode.
- If any consumer still imports deleted flow paths, hard-fail will surface immediately and must be retargeted to `shared_rust.services`.

# Handoff

## Session Summary
- DateTime (ET): 2026-03-31 09:49:16 -04:00
- Goal: Continue the `09:30:49 ET` ATM decay flat-row investigation by either tracing it to concrete leg quotes or adding post-lock flat-row diagnostics.
- Outcome: Complete for instrumentation. Existing logs proved the anomalous row was a real new snapshot write, but not which exact anchor-leg quote combination produced the flat `0/0/0`. The tracker now persists a dedicated `flat_post_lock_row` diagnostic with concrete call/put leg snapshots whenever that scenario is stored again.

## What Changed
- Code / Docs Files:
  - `l1_compute/analysis/atm_decay/tracker.py`
  - `l1_compute/tests/test_atm_decay_flat_post_lock_diagnostics.py`
  - `notes/sessions/2026-03-31/diagnose-post-lock-flat-atm-20260331/*`
- Runtime / Infra Changes:
  - No service restart in this session. Change is limited to L1 ATM decay diagnostics and focused tests.
- Commands Run:
  - `powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId diagnose-post-lock-flat-atm-20260331 -Title "Diagnose post-lock flat ATM row" -Scope implementation -UpdatePointer`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_flat_post_lock_diagnostics.py l1_compute/tests/test_atm_decay_tracker.py l1_compute/tests/test_atm_decay_anchor_recovery.py l1_compute/tests/test_atm_decay_modular.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_flat_post_lock_diagnostics.py l1_compute/tests/test_atm_decay_tracker.py l1_compute/tests/test_atm_decay_anchor_recovery.py l1_compute/tests/test_atm_decay_modular.py` (`33 passed`)
  - New regression coverage proves a post-lock flat row emits `flat_post_lock_row` diagnostics while the original opening-tick suppression path still emits nothing.
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` (`Session validation passed.`)
- Failed / Not Run:
  - Live root-cause replay was not possible retroactively because the already-stored 2026-03-31 `09:30:49 ET` row predates this instrumentation.
  - Initial `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` failed only because `meta.yaml.commands` did not yet include the strict-validation command evidence.

## Pending
- Must Do Next:
  - During the next market-hours reproduction, inspect `app:atm_anchor_diag:<YYYYMMDD>` or the cold diagnostic JSONL and match the `flat_post_lock_row` record to the stored ATM decay row.
- Nice to Have:
  - If the new evidence shows a stable benign flat market rather than quote-quality failure, decide whether UI or history should annotate that case instead of suppressing it.

## Debt Record (Mandatory)
OPENSPEC-EXEMPT: This is targeted L1 diagnostics inside the existing ATM decay contract; no new cross-layer contract surface or governance category was introduced.
SOP-EXEMPT: Current SOP already requires forensic logging for ATM anchor discard and diagnostic paths; this session adds instrumentation without changing runtime policy.
DEBT-EXEMPT: Remaining work is live evidence capture for the next reproduction, not deferred code scope from this patch.
DEBT-OWNER: Codex
DEBT-DUE: 2026-04-02
DEBT-RISK: Until a new live flat-row event is captured, the 2026-03-31 `09:30:49 ET` case remains underdetermined beyond sampled log evidence.
DEBT-NEW: 0
DEBT-CLOSED: 1
DEBT-DELTA: -1
DEBT-JUSTIFICATION: Closed the specific instrumentation gap that previously prevented successful flat-row writes from carrying leg-level evidence.
RUNTIME-ARTIFACT-EXEMPT: `tmp/pytest_cache` is the required isolated pytest cache; live diagnostic artifacts depend on a future market-hours reproduction.

## How To Continue
- Start Command: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
- Key Logs:
  - `logs/backend_runtime.current.log`
  - `data/atm_decay/diag/atm_anchor_diag_<YYYYMMDD>.jsonl`
- First File To Read: `notes/sessions/2026-03-31/diagnose-post-lock-flat-atm-20260331/handoff.md`

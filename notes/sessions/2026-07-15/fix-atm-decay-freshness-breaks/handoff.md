# Handoff

CHANGE-ID: impl-20260715-atm-decay-freshness-breaks
PROPOSAL-PATH: openspec/changes/impl-20260715-atm-decay-freshness-breaks/proposal.md
TASKS-PATH: openspec/changes/impl-20260715-atm-decay-freshness-breaks/tasks.md
STARTUP-PROOF: notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/startup.md

## Session Summary
- DateTime (ET): 2026-07-15 15:59 -04:00
- Goal: Fix ATM decay stale-source continuity, CALL/PUT leg freshness validation, stale-recovery L4 chart breaks, and suppressed roll-anchor `strike_changed`.
- Outcome: Runtime code implemented; Rust pyd rebuilt; targeted backend tests, L4 full tests, L4 build, and strict validation passed. Standard start-all was stopped by explicit user request after market close.

## What Changed
- Code / Docs Files:
  - `app/loops/atm_freshness.py`
  - `app/loops/anchor_mandatory_sync.py`
  - `app/loops/compute_loop.py`
  - `l1_compute/analysis/atm_decay/raw_pct.py`
  - `l1_compute/analysis/atm_decay/decay_output.py`
  - `l1_compute/analysis/atm_decay/anchor.py`
  - `l1_compute/analysis/atm_decay/tracker.py`
  - `shared/services/l0_runtime/state/runtime/__init__.py`
  - `shared_rust_services/src/atm_decay.rs`
  - `l4_ui/src/components/center/atmDecayChartData.ts`
  - `l4_ui/src/components/App.tsx`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L4_FRONTEND.md`
- Runtime / Infra Changes:
  - Rebuilt and installed `shared_rust/services.pyd` from `shared_rust_services`.
  - Stopped stale backend processes `15932` and `27172` to release the old pyd lock.
  - Included `data/cold` artifacts for 20260714 and 20260715 in the final repository commit so no untracked EOD artifacts remain.
- Commands Run:
  - `.\\.venv\\Scripts\\python.exe manage.py build-pyd --crate shared_rust_services`
  - `.\\.venv\\Scripts\\python.exe manage.py run-pytest app/loops/tests/test_anchor_mandatory_sync.py app/loops/tests/test_compute_loop_atm_live_continuity.py app/loops/tests/test_compute_loop_gpu_dedup.py app/tests/test_history_routes_v2.py l1_compute/tests/test_atm_decay_freshness.py`
  - `npm --prefix l4_ui run test -- atmDecayChartData`
  - `npm --prefix l4_ui run test`
  - `$env:VITE_BACKEND_ORIGIN='http://127.0.0.1:8001'; npm --prefix l4_ui run build`
  - `.\\.venv\\Scripts\\python.exe manage.py validate-session --strict`

## Verification
- Passed:
  - Rust pyd rebuild and install passed.
  - Targeted backend pytest: 22 passed.
  - L4 ATM chart data test: 6 passed.
  - L4 full Vitest suite: 228 passed.
  - L4 production build passed.
- Failed / Not Run:
  - Strict validation: passed.
- Failed / Not Run:
  - Standard `start-all`: user explicitly stopped this after market close; residual start-all processes were stopped.

VALIDATION-SUMMARY: Targeted pytest, L4 tests, L4 build, Rust pyd rebuild, and strict validation passed. Start-all was intentionally stopped by user.
COMMAND-EVIDENCE: build-pyd exited 0 after backend pyd lock was released; targeted pytest exited 0 with 22 passed; L4 full test exited 0 with 228 passed; L4 build exited 0; strict validation exited 0 with Session validation passed.
ACCEPTANCE-BUNDLE: N/A:command evidence is the acceptance record for this hotfix.
ACCEPTANCE-MODE: automated-tests + build + repo-strict-gate
ACCEPTANCE-RESULT: pass
ACCEPTANCE-EVIDENCE: Backend pytest 22 passed; L4 Vitest 228 passed; L4 build passed; strict validation passed.
HARNESS-IMPROVEMENT: Added backend ATM freshness regressions and L4 stale/gap whitespace chart regressions.
NOTES-PATHS: notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/; notes/context/project_state.md; notes/context/open_tasks.md; notes/context/handoff.md
CHANGED-PATHS: app/loops/atm_freshness.py; app/loops/anchor_mandatory_sync.py; app/loops/compute_loop.py; app/loops/shared_state.py; app/routes/history.py; app/tests/test_history_routes_v2.py; app/loops/tests/; l1_compute/analysis/atm_decay/; l1_compute/tests/test_atm_decay_freshness.py; l4_ui/src/components/App.tsx; l4_ui/src/components/center/atmDecayChartData.ts; l4_ui/src/components/center/__tests__/atmDecayChartData.test.ts; l4_ui/src/types/dashboard.ts; shared/services/l0_runtime/state/runtime/__init__.py; shared_rust_services/src/atm_decay.rs; shared_rust_services/src/lib.rs; data/cold/by_regime/balance_day/20260714/; data/cold/by_regime/balance_day/20260715/; data/cold/daily/20260714/; data/cold/daily/20260715/; data/cold/reports/20260714_quality.json; data/cold/reports/20260715_quality.json; docs/SOP/; openspec/changes/impl-20260715-atm-decay-freshness-breaks/; notes/
OPEN-RISKS: Standard start-all evidence deferred by explicit user request after market close; backend not left running.

FAST-FAIL-CHECK: Source stale samples fail closed by skipping ordinary ATM points; leg freshness mismatches reject samples.
NO-COMPAT-BRANCH: No Python fallback branch introduced for Rust raw pct.
NO-ROLLBACK-PATH: No runtime rollback path introduced.
NO-PATCH-BANDAGE: Fix carries source/leg freshness through backend payload and frontend rendering.
NO-FALLBACK-BEHAVIOR: No synthetic ATM samples are generated.

TRIGGER-PATHS: app/loops/atm_freshness.py; l1_compute/analysis/atm_decay/raw_pct.py; l4_ui/src/components/center/atmDecayChartData.ts
TRIGGER-BASIS: User-reported SPY ATM decay discontinuities around stale source windows and CALL/PUT leg inversion symptoms.
CHANGE-BEHAVIOR-CLASS: risk-control / fail-closed sample gating
TRIGGER-DECISION: Implement freshness provenance and chart discontinuity rather than smoothing stale points.
RESEARCH-PACKAGE-PATH: N/A:no separate research package created.
RESEARCH-REPORT: N/A:runtime hotfix with direct regression evidence.
RLLM-REPORT: N/A:no external RLLM review requested.
STRICT-COMMAND: `.\\.venv\\Scripts\\python.exe manage.py validate-session --strict` passed.

## Debt Record (Mandatory)
- DEBT-EXEMPT: No unchecked implementation tasks remain; start-all evidence deferred by explicit user direction after market close.
- DEBT-OWNER: N/A
- DEBT-DUE: 2026-07-15
- DEBT-RISK: Runtime health evidence is deferred; code/test/strict gates are green.
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: `shared_rust/services.pyd` rebuilt as runtime owner artifact; source changes are in `shared_rust_services`.

## How To Continue
- Start Command: `.\\.venv\\Scripts\\python.exe manage.py start-all`
- Key Logs: `logs/backend_runtime.current.log`
- First File To Read: `app/loops/atm_freshness.py`

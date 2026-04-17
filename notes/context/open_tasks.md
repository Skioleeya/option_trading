# Open Tasks (Index)

## Active Session Tasks
- Path: notes/sessions/2026-04-17/impl-l4-center-header-adaptive-layout/open_tasks.md

## Global Backlog (Cross-Session)
- [ ] Complete wave6 strict validation pass evidence and attach command output to session handoff.
- [ ] Execute postmarket 120-second live runtime verification (Redis/backend/frontend + mm_flow key metrics non-zero evidence).
- [ ] Add dedicated model test for duplicate/out-of-range `slot_index` sanitation in ActiveOptions.
- [ ] Monitor strict startup gate telemetry for `writer_not_ready_timeout` in live market open window; retune timeout only with evidence.
- [ ] Capture one full market-session Sub-wave F dual-run compare and append no-divergence evidence in handoff.
- [ ] Verify/close residual `tmp/pytest_cache` write-warning path (`nodeids`) for non-escalated test runs.
- [ ] Continue `shared/services` retirement with `l0_runtime` (Sub-wave D storage/utility assessment completed; tactical-triad wrapper retirement closed in Wave B; next: namespace convergence and remaining neutral-surface retirements).
- [ ] Collapse temporary Rust-only service module names into the final `shared_rust.services` namespace.
- [x] **DEBT-L1-1 CLOSED (2026-04-02, impl-20260402-claude-audit-fixes-closeout)** `l1_compute/analysis/bsm_aggregation.py` Rust owner migration closed.
- [x] **DEBT-L1-2 CLOSED (2026-04-02, impl-20260402-claude-audit-fixes-closeout)** `l1_compute/aggregation/zero_gamma.py` Rust owner migration closed.

## Session-Specific Status
- [x] L4 header grouped masthead structure landed.
- [x] IV detail badge readability pass landed.
- [x] SPY broker-style tick feedback landed.
- [x] Header `SCALE` display removed and right-rail spacing cleaned up.
- [x] Targeted frontend tests passed for the affected modules.
- [x] Strict validation pass evidence recorded for the active session.

## Process
- Task details and completion evidence belong in the session-local open_tasks.md.
- Keep this file as the long-horizon queue and session pointer only.

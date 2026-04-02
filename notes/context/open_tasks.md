# Open Tasks (Index)

## Active Session Tasks
- Path: notes/sessions/2026-04-02/impl-20260402-active-options-pure-shim-retirement-closeout/open_tasks.md

## Global Backlog (Cross-Session)
- [ ] Capture one full market-session Sub-wave F dual-run compare and append no-divergence evidence in handoff.
- [ ] Verify/close residual `tmp/pytest_cache` write-warning path (`nodeids`) for non-escalated test runs.
- [ ] Continue `shared/services` retirement with `l0_runtime` (Sub-wave D storage/utility assessment completed; tactical-triad wrapper retirement closed in Wave B; next: namespace convergence and remaining neutral-surface retirements).
- [ ] Collapse temporary Rust-only service module names into the final `shared_rust.services` namespace.
- [x] **DEBT-L1-1 CLOSED (2026-04-02, impl-20260402-claude-audit-fixes-closeout)** `l1_compute/analysis/bsm_aggregation.py` 已删除；`bsm_fast.py` 聚合改由 Rust owner `aggregate_from_greeks` 承担。Ref: openspec/changes/impl-20260402-l1-bsm-numpy-rust-fallback/tasks.md
- [x] **DEBT-L1-2 CLOSED (2026-04-02, impl-20260402-claude-audit-fixes-closeout)** `l1_compute/aggregation/zero_gamma.py` 已删除；`streaming_aggregator` zero-gamma 改由 Rust owner `estimate_zero_gamma_level` 承担。Ref: openspec/changes/impl-20260402-l1-streaming-aggregator-rust/tasks.md

## Process
- Task details and completion evidence belong in the session-local open_tasks.md.
- Keep this file as the long-horizon queue and session pointer only.

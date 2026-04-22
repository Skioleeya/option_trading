# Project State

## Snapshot
- DateTime (ET): 2026-03-13 09:46:47 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `f8a9b52`
- Environment:
  - Market: `CLOSED` (not probed in this session)
  - Data Feed: `UNKNOWN` (not probed in this session)
  - L0-L4 Pipeline: `UNKNOWN` (not probed in this session)

## Current Focus
- Primary Goal: complete Phase F guard unit/reference sync and bring `tasks.md` to done with executable evidence.
- Scope In:
  - `VRPVetoGuard` unit normalization to `% points`
  - Legacy decimal threshold compatibility (`0.15/0.13 -> 15.0/13.0`)
  - IV metrics map + SOP guard semantic boundary sync
  - Targeted pytest evidence for guard + helper paths
  - Strict session validation pass
- Scope Out:
  - Phase G/H runtime cutover and parent proposal final closure
  - Non-Phase-F runtime refactors unrelated to guard contract

## What Changed (Latest Session)
- Files:
  - `l2_decision/guards/rail_engine.py`
  - `l2_decision/tests/test_reactor_and_guards.py`
  - `shared/tests/test_metric_semantics.py`
  - `docs/IV_METRICS_MAP.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
  - `openspec/changes/formula-semantic-followup-phase-f-guard-unit-and-reference-sync/tasks.md`
  - `notes/sessions/2026-03-13/formula-semantic-followup-phase-f-guard-unit-and-reference-sync-impl/*`
- Behavior:
  - `VRPVetoGuard` now computes `guard_vrp_proxy_pct` via shared helper and evaluates in `% points`.
  - Guard thresholds now normalize legacy decimal inputs to percent-point contract.
  - Operator/SOP docs now explicitly separate `vol_risk_premium` (live feature proxy) and `guard_vrp_proxy_pct` (guard-only heuristic proxy).
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l2_decision/tests/test_reactor_and_guards.py shared/tests/test_metric_semantics.py` (PASS: 63 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` (run #1 FAIL metadata evidence, run #2 PASS)

## Risks / Constraints
- Risk 1: worktree contains many pre-existing unrelated changes; this session only modifies Phase F relevant files.
- Risk 2: parent governance closure still depends on downstream Phase G/H completion.

## Next Action
- Immediate Next Step: start Phase G (`live canonical contract cutover`) based on completed Phase F contract baseline.
- Owner: Codex / next implementing agent

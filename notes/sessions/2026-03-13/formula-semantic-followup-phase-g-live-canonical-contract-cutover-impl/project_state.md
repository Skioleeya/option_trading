# Project State

## Snapshot
- DateTime (ET): 2026-03-13 10:01:51 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `f8a9b52`
- Environment:
  - Market: `CLOSED` (not probed in this session)
  - Data Feed: `UNKNOWN` (not probed in this session)
  - L0-L4 Pipeline: `UNKNOWN` (not probed in this session)

## Current Focus
- Primary Goal: complete Phase G live canonical source cutover while preserving payload schema compatibility.
- Scope In:
  - L3 `ui_state.skew_dynamics` live source -> `rr25_call_minus_put` + `skew_25d_valid` gate
  - L3 `ui_state.tactical_triad.charm` live source -> `net_charm_raw_sum`
  - L3/L4 regression tests + SOP sync + OpenSpec task closure + strict gate
- Scope Out:
  - Payload top-level schema shape changes
  - Phase H reconciliation and parent final closure

## What Changed (Latest Session)
- Files:
  - `l3_assembly/assembly/ui_state_tracker.py`
  - `l3_assembly/tests/test_ui_state_tracker.py`
  - `l3_assembly/tests/test_reactor.py`
  - `l4_ui/src/components/__tests__/skewDynamics.model.test.ts`
  - `l4_ui/src/components/__tests__/tacticalTriad.model.test.ts`
  - `l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `openspec/changes/formula-semantic-followup-phase-g-live-canonical-contract-cutover/tasks.md`
  - `notes/sessions/2026-03-13/formula-semantic-followup-phase-g-live-canonical-contract-cutover-impl/*`
- Behavior:
  - L3 skew live mapping now reads canonical `rr25_call_minus_put` only (with existing validity gate).
  - L3 tactical charm live mapping now reads canonical `net_charm_raw_sum` only.
  - Payload top-level fields/schema envelope unchanged; legacy lower-layer fields remain compatibility/research path only.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_ui_state_tracker.py l3_assembly/tests/test_reactor.py` (PASS: 25 passed)
  - `npm --prefix l4_ui run test -- rightPanelContract.integration skewDynamics.model tacticalTriad.model` (run #1 sandbox EPERM, run #2 PASS: 10 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` (run #1 FAIL evidence missing in meta, run #2 PASS)

## Risks / Constraints
- Risk 1: worktree has many pre-existing unrelated modifications; this session only touched Phase G scope.
- Risk 2: parent governance closure still blocked by Phase H completion.

## Next Action
- Immediate Next Step: start Phase H (`openspec reconciliation`) and then close parent governance proposal.
- Owner: Codex / next implementing agent

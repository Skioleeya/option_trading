# Project State

## Snapshot
- DateTime (ET): 2026-03-06 12:59:49 -05:00
- Branch: `master`
- Last Commit: `5a88b76`
- Environment:
  - Market: `OPEN`
  - Data Feed: `NOT VERIFIED`
  - L0-L4 Pipeline: `NOT VERIFIED`

## Current Focus
- Primary Goal: Audit MicroStats L0-L4 path and hotfix severe state/color regressions.
- Scope In:
  - MicroStats state contract wiring (`wall_dyn`) in L3 assembler
  - MicroStats badge token normalization (L3 presenter + payload contract)
  - Vanna grind-threshold sign guard (state threshold sanity)
  - Regression tests for microstats + vanna classification
- Scope Out:
  - Unrelated presenter debt in `l3_assembly/tests/test_presenters.py`
  - Non-MicroStats UI redesign work

## What Changed (Latest Session)
- Files:
  - `l3_assembly/events/payload_events.py`
  - `l3_assembly/presenters/micro_stats.py`
  - `l3_assembly/assembly/payload_assembler.py`
  - `l1_compute/trackers/vanna_flow_analyzer.py`
  - `l3_assembly/tests/test_assembly.py`
  - `l1_compute/tests/test_vanna_flow_analyzer.py`
- Behavior:
  - Fixed `wall_dyn` wiring gap: MicroStats now receives wall states from `ui_metrics.wall_migration_data`.
  - Fixed badge collapse: MicroStats no longer downgrades all state badges to `badge-neutral`.
  - Expanded MetricCard accepted badge tokens to match frontend badge classes.
  - Added vanna threshold sign guard: `GRIND_STABLE` now requires negative correlation by forcing threshold to `-abs(...)`.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\test\run_pytest.ps1 l3_assembly/tests/test_assembly.py l1_compute/tests/test_vanna_flow_analyzer.py -q` (28 passed)
  - Reproducer confirms micro_stats now outputs:
    - `net_gex`: `badge-hollow-green`
    - `wall_dyn`: `PINCH` + `badge-purple`
    - `vanna`: `badge-red`
    - `momentum`: `badge-red`

## Risks / Constraints
- Risk 1: Full live UI websocket validation not run in this session.
- Risk 2: Existing unrelated failures remain in `l3_assembly/tests/test_presenters.py`.

## Next Action
- Immediate Next Step: Run backend+frontend live feed and confirm MicroStats colors and wall state transition behavior in-panel.
- Owner: Codex

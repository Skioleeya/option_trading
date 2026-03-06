# Project State

## Snapshot
- DateTime (ET): 2026-03-06 13:18:22 -05:00
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
  - Wall dynamics extreme-state handling (`BREACHED/DECAYING/UNAVAILABLE`) and debounce policy
  - MicroStats wall-dynamics modularization into dedicated state machine
  - Regression tests for microstats + vanna classification
- Scope Out:
  - Unrelated presenter debt in `l3_assembly/tests/test_presenters.py`
  - Non-MicroStats UI redesign work

## What Changed (Latest Session)
- Files:
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `docs/SOP/L4_FRONTEND.md`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `l3_assembly/presenters/ui/micro_stats/wall_dynamics.py`
  - `l3_assembly/presenters/ui/micro_stats/presenter.py`
  - `l3_assembly/presenters/ui/micro_stats/thresholds.py`
  - `l3_assembly/presenters/ui/micro_stats/mappings.py`
  - `l3_assembly/presenters/ui/micro_stats/palette.py`
  - `l3_assembly/tests/test_micro_stats_wall_dynamics.py`
- Behavior:
  - SOP 文档已同步本次 hotfix + modularization：补充 `WALL DYN` 状态机边界、`BREACH` urgent 规则、Vanna 负阈值守卫、L4 颜色语义契约。
  - Fixed severe masking bug: `WALL DYN` no longer maps `BREACHED/DECAYING/UNAVAILABLE` to `STABLE`.
  - Added urgent-state bypass: `BREACH` now bypasses debounce and appears on first tick.
  - Extracted wall composite-key logic into pure module `wall_dynamics.py` (modularization).
  - Extended wall mapping/palette to include `BREACH`, `DECAY`, `UNAVAILABLE`.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\test\run_pytest.ps1 l3_assembly/tests/test_micro_stats_wall_dynamics.py l3_assembly/tests/test_assembly.py l1_compute/tests/test_vanna_flow_analyzer.py -q` (32 passed)
  - Reproducer confirms `BREACHED + STABLE` now yields `wall_dyn: BREACH` (previously `STABLE`).
  - `powershell -ExecutionPolicy Bypass -File .\scripts\validate_session.ps1` (passed)

## Risks / Constraints
- Risk 1: Full live UI websocket validation not run in this session.
- Risk 2: Existing unrelated failures remain in `l3_assembly/tests/test_presenters.py`.

## Next Action
- Immediate Next Step: Run backend+frontend live feed and confirm MicroStats colors and wall state transition behavior in-panel.
- Owner: Codex

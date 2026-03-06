# Project State

## Snapshot
- DateTime (ET): 2026-03-06 12:44:21 -05:00
- Branch: `master`
- Last Commit: `5a88b76`
- Environment:
  - Market: `OPEN`
  - Data Feed: `NOT VERIFIED`
  - L0-L4 Pipeline: `NOT VERIFIED`

## Current Focus
- Primary Goal: Fix DepthProfile `macro_volume_map` loss on L0→L4 typed pipeline.
- Scope In:
  - `app/loops/compute_loop.py` metadata pass-through modularization
  - `l3_assembly/assembly/payload_assembler.py` typed snapshot extraction fix
  - `l3_assembly/tests/test_assembly.py` regression coverage
- Scope Out:
  - Unrelated presenter test debt (`l3_assembly/tests/test_presenters.py` existing failures)
  - UI visual redesign work in `l4_ui/src/components/left/DepthProfile.tsx`

## What Changed (Latest Session)
- Files:
  - `app/loops/compute_loop.py`
  - `l3_assembly/assembly/payload_assembler.py`
  - `l3_assembly/tests/test_assembly.py`
- Behavior:
  - Added modular L0→L1 metadata builder to include normalized `volume_map` in `extra_metadata`.
  - Added `PayloadAssemblerV2` volume-map normalization and typed snapshot extraction from `extra_metadata`.
  - Fixed typed path contract gap where `ui_state.macro_volume_map` was always `{}`.
  - Added regression test to lock macro-volume passthrough behavior.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\test\run_pytest.ps1 l3_assembly/tests/test_assembly.py -q` (24 passed)
  - Local reproducer before fix: `macro_volume_map` was `{}` even with metadata.
  - Local reproducer after fix: `macro_volume_map` contains expected strike-volume entries.

## Risks / Constraints
- Risk 1: End-to-end WS runtime verification (actual UI minimap render) not executed in this session.
- Risk 2: `l3_assembly/tests/test_presenters.py` has pre-existing unrelated failures; not in hotfix scope.

## Next Action
- Immediate Next Step: Run live backend+frontend tick and verify `DepthProfile` minimap updates from live `volume_map`.
- Owner: Codex

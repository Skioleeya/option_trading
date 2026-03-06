# Handoff

## Session Summary
- DateTime (ET): 2026-03-06 12:44:21 -05:00
- Goal: Audit `l4_ui/src/components/left/DepthProfile.tsx` full L0-L4 business path and fix severe defects.
- Outcome: Confirmed severe typed-pipeline contract break (`macro_volume_map` dropped), applied hotfix + modularization, and added regression test.

## What Changed
- Code / Docs Files:
  - `app/loops/compute_loop.py`
  - `l3_assembly/assembly/payload_assembler.py`
  - `l3_assembly/tests/test_assembly.py`
  - `notes/sessions/2026-03-06/1241/1338_depth_profile_l0_l4_hotfix_mod/project_state.md`
  - `notes/sessions/2026-03-06/1241/1338_depth_profile_l0_l4_hotfix_mod/open_tasks.md`
  - `notes/sessions/2026-03-06/1241/1338_depth_profile_l0_l4_hotfix_mod/handoff.md`
  - `notes/sessions/2026-03-06/1241/1338_depth_profile_l0_l4_hotfix_mod/meta.yaml`
- Runtime / Infra Changes:
  - None.
- Commands Run:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\new_session.ps1 -TaskId "1338_depth_profile_l0_l4_hotfix_mod" ... -UseTimeBucket`
  - `powershell -ExecutionPolicy Bypass -File .\scripts\test\run_pytest.ps1 l3_assembly/tests/test_assembly.py -q`
  - Python reproducer (before/after) for `PayloadAssemblerV2` macro-volume passthrough.

## Verification
- Passed:
  - `l3_assembly/tests/test_assembly.py`: 24 passed.
  - Reproducer confirms `ui_state.macro_volume_map` now populated in typed snapshot path.
- Failed / Not Run:
  - `l3_assembly/tests/test_presenters.py` has pre-existing unrelated failures (not modified in this session).
  - No live frontend runtime verification was executed.

## Pending
- Must Do Next:
  - Start backend+frontend and verify `DepthProfile` minimap updates live under L2 path.
- Nice to Have:
  - Add UI-level automated test for minimap presence when `macro_volume_map` exists.

## How To Continue
- Start Command:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\test\run_pytest.ps1 l3_assembly/tests/test_assembly.py -q`
- Key Logs:
  - `[Debug] L0 Fetch: rust_active=... shm_stats=True`
  - L3 payload should carry `agent_g.data.ui_state.macro_volume_map` non-empty when L0 volume research is available.
- First File To Read:
  - `l3_assembly/assembly/payload_assembler.py`

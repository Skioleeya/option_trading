# Project State

## Snapshot
- DateTime (ET): 2026-03-25 23:19:09 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `2b286ae21d1d14cc1f07b6511d62e0842fa43ca8`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: capture live `dashboard_delta` behavior and surface canonical `net_vanna_raw_sum` to L4 as an explicit raw-vanna card.
- Scope In:
  - live WebSocket frame capture on `/ws/dashboard`
  - L3 diagnostic payload threading via existing `micro_structure` channel
  - L4 Right Panel raw-vanna normalization and rendering
  - SOP/OpenSpec/session governance updates
- Scope Out:
  - no L1/L2 Greek formula changes
  - no TacticalTriad/MicroStats contract expansion
  - no store/delta-decoder redesign

## What Changed (Latest Session)
- Files:
  - `l3_assembly/assembly/ui_state_tracker.py`
  - `l3_assembly/tests/test_ui_state_tracker.py`
  - `l4_ui/src/types/dashboard.ts`
  - `l4_ui/src/components/right/rightPanelModel.ts`
  - `l4_ui/src/components/right/RawVannaCard.tsx`
  - `l4_ui/src/components/right/RightPanel.tsx`
  - `l4_ui/src/components/__tests__/rightPanelModel.test.ts`
  - `l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `docs/SOP/L4_FRONTEND.md`
  - `openspec/changes/live-raw-vanna-diagnostic-card-20260325/*`
- Behavior:
  - L3 now injects canonical `net_vanna_raw_sum` into `agent_g.data.micro_structure.micro_structure_state`.
  - L4 Right Panel now renders a dedicated `RAW VANNA` diagnostic card from the existing `micro_structure` channel.
  - Live capture confirmed `dashboard_delta` remains heartbeat-dominant after hours, while true metric refreshes arrive sparsely via `agent_g_data.micro_structure`, `net_gex`, `tactical_triad`, and `active_options`.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_ui_state_tracker.py`
  - `npm --prefix l4_ui run test -- rightPanelModel rightPanelContract`
  - live `/ws/dashboard` capture after backend restart confirmed `net_vanna_raw_sum` in `dashboard_init` and subsequent `agent_g_data.micro_structure` deltas

## Risks / Constraints
- Risk 1: after-hours cadence is source-dedup dominated; most `dashboard_delta` frames only carry heartbeat/is_stale, so “continuous refresh” during closed market should not be interpreted as per-tick metric recompute.
- Risk 2: worktree contains unrelated pre-existing modifications from adjacent sessions; this session must not revert them.

## Next Action
- Immediate Next Step: run strict validation, then preserve this session as the active handoff pointer.
- Owner: Codex

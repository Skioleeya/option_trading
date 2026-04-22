# Project State

## Snapshot
- DateTime (ET): 2026-03-26 15:51:30 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `3eb64de`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: implement the title-bar IV dynamic-threshold enhancement end-to-end, including OpenSpec, L0 auxiliary diagnostics, L3 payload contract, and L4 header rendering.
- Scope In:
  - `app/loops/payload_debug.py`
  - `app/routes/health.py`
  - `shared/services/l0_runtime/services/orchestration/*`
  - `shared/services/header_volatility_context.py`
  - `l3_assembly/*`
  - `l4_ui/src/components/center/Header.tsx`
  - `l4_ui/src/store/dashboardStore.ts`
  - `l4_ui/src/types/dashboard.ts`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `docs/SOP/L4_FRONTEND.md`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `openspec/changes/header-iv-dynamic-threshold-context-20260326/*`
- Scope Out:
  - no L2 decision-weight change
  - no strategy/risk threshold retune
  - no replacement of existing `spy_atm_iv` or `iv_regime` semantics

## What Changed (Latest Session)
- Files:
  - `app/loops/payload_debug.py`
  - `app/routes/health.py`
  - `app/loops/tests/test_payload_debug.py`
  - `app/tests/test_health_route_diagnostics.py`
  - `shared/services/l0_runtime/services/orchestration/orchestrator.py`
  - `shared/services/l0_runtime/services/orchestration/header_volatility_support.py`
  - `shared/services/l0_runtime/projection/snapshot/components.py`
  - `shared/services/l0_runtime/projection/snapshot/payload.py`
  - `shared/services/header_volatility_context.py`
  - `app/loops/compute_metadata.py`
  - `l3_assembly/assembly/payload_assembler.py`
  - `l3_assembly/assembly/payload_assembler_support.py`
  - `l3_assembly/assembly/ui_state_tracker.py`
  - `l3_assembly/events/payload_events.py`
  - `l3_assembly/events/payload_ui_state.py`
  - `l3_assembly/reactor.py`
  - `l4_ui/src/components/center/Header.tsx`
  - `l4_ui/src/store/dashboardStore.ts`
  - `l4_ui/src/types/dashboard.ts`
  - `openspec/changes/header-iv-dynamic-threshold-context-20260326/*`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `docs/SOP/L4_FRONTEND.md`
- Behavior:
  - L0 now emits low-frequency title-bar auxiliary diagnostics for `.VIX.US` and `1DTE ATM IV`
  - a new shared context service computes `IVR/IVP`, `term_structure`, and `120s ΔIV / ΔPrice`
  - L3 now exposes `agent_g.data.header_volatility`
  - `[L3-PAYLOAD]` now emits a dedicated `header_volatility` summary line once the title-bar context contract is present
  - `/debug/persistence_status` now exposes both `header_volatility.payload` and `l1_runtime.header_volatility_aux` for live continuity checks
  - L4 Header now renders compact `R/P/1D/VX/β` tokens while preserving existing main IV display
  - the oversized L3 payload modules were split so changed runtime files stay under the 400-line gate
  - an elevated degraded backend restart was required to replace the old live instance because strict startup connectivity probing is still blocked by `/v2/socket/token`
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/loops/tests/test_payload_debug.py app/tests/test_health_route_diagnostics.py -q`
  - `python -m compileall app/loops/payload_debug.py app/routes/health.py shared/services/l0_runtime/services/orchestration/orchestrator.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -Degraded -LogFile logs/backend_runtime.header_volatility_debug.log`
  - `Invoke-RestMethod http://127.0.0.1:8001/debug/persistence_status` sampled repeatedly and showed aligned, advancing `l1_version/payload_version/source_version`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_header_volatility_context.py l3_assembly/tests/test_ui_state_tracker.py l3_assembly/tests/test_payload_events.py l3_assembly/tests/test_reactor.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_assembly.py app/loops/tests/test_compute_loop_helpers.py -q`
  - `npm --prefix l4_ui run test -- header.render`
  - `npm --prefix l4_ui run build`
  - `python -m compileall ...`

## Risks / Constraints
- Risk 1: strict startup remains blocked in this environment when the quote runtime connectivity probe cannot acquire `/v2/socket/token`; degraded restart is currently the only verified fresh-launch path.
- Risk 1: `1DTE` expiry currently uses weekday-based next-trading-day inference at this layer; exchange holiday calendars are not yet injected here.
- Risk 2: `IVR/IVP` depends on the research feature store retaining enough completed-day ATM IV samples; sparse historical stores degrade to unavailable by design.

## Next Action
- Immediate Next Step: hand off the validated change set or commit/push it if requested.
- Owner: Codex

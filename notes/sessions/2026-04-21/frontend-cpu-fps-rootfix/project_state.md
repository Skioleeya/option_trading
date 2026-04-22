# Project State

## Snapshot
- DateTime (ET): 2026-04-21 16:33:30 -04:00
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Keep the live L4 dashboard under the browser CPU/FPS budget on the standard `start-all` dev path.
- Scope In: `l4_ui` hot-path rerender elimination, ATM history store hot-path removal, profiling/measurement hooks, session/SOP sync.
- Scope Out: L0-L3 runtime semantics, broker contracts, new UI feature work.

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/hooks/useDashboardWS.ts`
  - `l4_ui/src/components/App.tsx`
  - `l4_ui/src/observability/l4_rum.ts`
  - `l4_ui/src/components/center/AtmDecayChart.tsx`
  - `l4_ui/src/components/center/atmDecayChartData.ts`
  - `l4_ui/src/components/left/LeftPanel.tsx`
  - `l4_ui/src/components/right/RightPanel.tsx`
  - `l4_ui/src/components/right/MmFlowCard.tsx`
  - `l4_ui/src/components/right/mmFlowModel.ts`
  - `l4_ui/src/alerts/alertEngine.ts`
  - `l4_ui/src/components/right/ActiveOptions.tsx`
  - `l4_ui/src/components/right/activeOptionsTheme.ts`
  - `l4_ui/src/components/right/decisionEngineModel.ts`
  - `l4_ui/src/components/right/mtfFlowModel.ts`
  - `l4_ui/src/components/left/DepthProfile.tsx`
  - `l4_ui/src/main.tsx`
  - `l4_ui/src/smoke_test.ts`
  - `l4_ui/src/store/dashboardStore.ts`
  - `l4_ui/src/store/dashboardStore.helpers.ts`
  - `l4_ui/src/observability/__tests__/l4_rum.test.ts`
  - `l4_ui/src/components/center/__tests__/atmDecayChartData.test.ts`
  - `l4_ui/src/components/__tests__/debugHotkey.integration.test.tsx`
  - `l4_ui/src/components/__tests__/smallWindowGuardrails.test.tsx`
  - `l4_ui/src/store/__tests__/dashboardStore.test.ts`
  - `docs/SOP/L4_FRONTEND.md`
- Behavior:
  - `App` no longer rerenders on every websocket message; websocket bootstrap is side-effect-only.
  - Debug overlay is no longer mounted while closed.
  - RUM profiling can run without rendering the overlay, via `l4:set_profiling_enabled` / `mockL4.setProfiling()`.
  - `AtmDecayChart` hot path uses incremental stream sync instead of full-history rebuilds.
  - Stable-only payload subscriptions were removed from the default live left/right panel path.
  - `AlertEngine` now subscribes to a narrow selector instead of the full store.
  - `dashboardStore` ATM history maintenance is trade-date keyed and O(1) on live ticks; the previous per-tick ET date filter is gone.
- Verification:
  - Targeted vitest suites passed.
  - Real-host `start-all` succeeded.
  - Real Windows Chrome CDP sampling reached `cpu_avg_pct=4.49`, `fps_avg=60`, `fps_min=60`, `fps_samples_below_50=0`.

## Risks / Constraints
- Risk 1: `npm --prefix l4_ui run build` is still blocked by unrelated pre-existing TypeScript test typing debt outside this session’s runtime hot path.
- Risk 2: Browser CPU evidence is from real-host headless Chrome on the standard dev server path; a different local browser extension set or non-headless renderer can shift the exact margin.

## Next Action
- Immediate Next Step: Run strict validation, then archive this session as the active frontend performance baseline.
- Owner: Codex

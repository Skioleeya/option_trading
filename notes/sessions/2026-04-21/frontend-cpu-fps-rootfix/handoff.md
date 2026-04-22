# Handoff

## Session Summary
- DateTime (ET): 2026-04-21 16:33:30 -04:00
- Goal: Bring live frontend browser CPU below `5%` and keep FPS above `50` on the standard `python3 manage.py start-all` dev path.
- Outcome: COMPLETE. Real-host headless Chrome sampling on the live dashboard ended at `cpu_avg_pct=4.49`, `cpu_max_pct=11.59`, `fps_avg=60`, `fps_min=60`, `fps_samples_below_50=0`.

## What Changed
- Code / Docs Files:
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
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-04-21/frontend-cpu-fps-rootfix/project_state.md`
  - `notes/sessions/2026-04-21/frontend-cpu-fps-rootfix/open_tasks.md`
  - `notes/sessions/2026-04-21/frontend-cpu-fps-rootfix/handoff.md`
  - `notes/sessions/2026-04-21/frontend-cpu-fps-rootfix/meta.yaml`
- Runtime / Infra Changes:
  - Real-host startup executed with `python3 manage.py start-all` held alive long enough for Windows-side headless Chrome measurement.
  - Windows Chrome headless remote-debugging session on port `9223` used for CPU/FPS evidence.
- Commands Run:
  - `python3 manage.py new-session --task-id frontend-cpu-fps-rootfix`
  - `npm --prefix l4_ui run test -- src/components/__tests__/debugOverlayModel.test.ts src/adapters/__tests__/protocolAdapter.test.ts src/components/__tests__/activeOptions.render.test.tsx src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `npm --prefix l4_ui run test -- src/components/__tests__/debugHotkey.integration.test.tsx src/observability/__tests__/l4_rum.test.ts src/components/center/__tests__/atmDecayChartData.test.ts src/store/__tests__/dashboardStore.test.ts`
  - `python3 manage.py start-all`
  - Windows headless Chrome launch with remote debugging on `9223`
  - Windows PowerShell CDP sampling scripts via `tmp/chrome_perf_sample.ps1` and `tmp/chrome_cpu_profile.ps1`

## Verification
- Passed:
  - Root-cause profiling before the store fix showed the hottest frontend CPU frames inside `src/store/dashboardStore.helpers.ts`, especially `getEtTradeDateKeyFromTimestamp` and `keepHistoryWithinTradeDate`, proving `atmHistory` trade-date filtering was still happening on every payload.
  - First real-browser samples established the reduction ladder:
    - before store fix: `cpu_avg_pct=13.35`, `fps_avg=60`
    - after partial hot-path cuts only: `cpu_avg_pct=7.70`, `fps_avg=60`
    - after `dashboardStore` trade-date keyed O(1) live history fix: `cpu_avg_pct=4.49`, `cpu_max_pct=11.59`, `fps_avg=60`, `fps_min=60`, `fps_samples_below_50=0`
  - Final Chrome metric breakdown after the winning fix:
    - `script_avg_pct=0.81`
    - `layout_avg_pct=0.34`
    - `style_avg_pct=0.13`
  - Final Chrome CPU profile no longer shows `dashboardStore.helpers.ts` as a hotspot; remaining activity is mostly idle with low-level React dev/runtime work.
  - Targeted vitest suites passed:
    - `src/store/__tests__/dashboardStore.test.ts`
    - `src/observability/__tests__/l4_rum.test.ts`
    - `src/components/center/__tests__/atmDecayChartData.test.ts`
    - `src/components/__tests__/debugHotkey.integration.test.tsx`
    - `src/components/__tests__/debugOverlayModel.test.ts`
    - `src/adapters/__tests__/protocolAdapter.test.ts`
    - `src/components/__tests__/activeOptions.render.test.tsx`
    - `src/components/__tests__/rightPanelContract.integration.test.tsx`
- Strict Validation:
  - `python3 manage.py validate-session --strict` first run: quality gate PASS, openspec gate PASS, then failed only because `meta.yaml` commands and `handoff.md` were missing strict-validation evidence lines.
  - Notes were updated and the rerun passed with `Session validation passed.`

- Failed / Not Run:
  - `npm --prefix l4_ui run build` still hits unrelated pre-existing TypeScript test typing failures outside the hot-path code touched here (`smallWindowGuardrails`, tactical-triad test debt, node type declarations). The runtime CPU/FPS fix itself was verified through targeted tests and real browser evidence.

## Pending
- Must Do Next:
  - Clear the unrelated frontend type-test debt so full `npm run build` becomes green again.
- Nice to Have:
  - Re-run the same CDP sampling in a headed Windows Chrome session during a higher-volatility market window for an additional evidence pack.

SOP Files Updated:
- `docs/SOP/L4_FRONTEND.md`
OPENSPEC-EXEMPT: Frontend performance hot-path repair only; no payload contract, backend contract, or product behavior spec changed.

## Debt Record (Mandatory)
- DEBT-EXEMPT:
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-23
- DEBT-RISK: Medium. Full frontend `build` remains blocked by unrelated type-test debt even though the live performance budget is now met.
- DEBT-NEW: 0
- DEBT-CLOSED: 1
- DEBT-DELTA: -1
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: Windows headless Chrome and CDP sampling scripts were verification-only artifacts.

## How To Continue
- Start Command:
  - `python3 manage.py start-all`
- Key Logs:
  - `logs/backend_runtime.current.log`
  - `logs/frontend_runtime.current.log`
  - `tmp/chrome_perf_sample.json`
  - `tmp/chrome_cpu_profile.json`
- First File To Read:
  - `notes/sessions/2026-04-21/frontend-cpu-fps-rootfix/handoff.md`

# Handoff

## Session Summary
- DateTime (ET): 2026-04-23 08:04:15 -04:00
- Goal: investigate the frontend error `ATM HISTORY FAST-FAIL: [App] ATM history is empty; persistence is required in strict mode.` and fix the root cause without masking real RTH persistence failures.
- Outcome: root cause confirmed and fixed. The bug was a frontend-only false positive: premarket same-day ATM history is legitimately empty before `09:30 ET`, but `App.tsx` treated any empty history as a strict failure. L4 now fast-fails only during `OPEN` RTH; outside RTH it preserves the intended `-- PENDING` state.

## What Changed
- Code / Docs Files:
  - `l4_ui/src/components/App.tsx`
  - `l4_ui/src/components/__tests__/atmHistoryHydrate.test.tsx`
  - `docs/SOP/L4_FRONTEND.md`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-04-23/atm-history-strict-fail/project_state.md`
  - `notes/sessions/2026-04-23/atm-history-strict-fail/open_tasks.md`
  - `notes/sessions/2026-04-23/atm-history-strict-fail/handoff.md`
  - `notes/sessions/2026-04-23/atm-history-strict-fail/meta.yaml`
- Runtime / Infra Changes:
  - No backend/tracker persistence behavior was changed.
  - L4 cold-boot ATM hydrate now requires non-empty history only when `deriveMarketStatus() === 'OPEN'`.
  - Outside RTH, empty same-day ATM history is treated as a legal pending state rather than a strict failure.
- Commands Run:
  - `.\.venv\Scripts\python.exe manage.py new-session --task-id atm-history-strict-fail --title "atm history strict fail" --scope infra --owner Codex --parent-session 2026-04-23/start-all-health-check --update-pointer`
  - `Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:5173/api/atm-decay/history?fields=timestamp%2Cstraddle_pct%2Ccall_pct%2Cput_pct%2Cstrike_changed&schema=v2"`
  - `.\.venv\Scripts\python.exe -c "from websockets.sync.client import connect; ... ws://127.0.0.1:5173/ws/dashboard ..."`
  - `Get-ChildItem data\atm_decay`
  - `npm --prefix l4_ui run test -- atmHistoryHydrate`
  - `npm --prefix l4_ui run test -- debugHotkey.integration`
  - `$env:VITE_BACKEND_ORIGIN='http://127.0.0.1:8001'; npm --prefix l4_ui run build`
  - `.\.venv\Scripts\python.exe manage.py validate-session --strict`

## Verification
- Passed:
  - Live host reproduction: same-origin `/api/atm-decay/history?...&schema=v2` returned `{"count":0,"date":"20260423"}` before RTH.
  - Live host reproduction: same-origin `ws://127.0.0.1:5173/ws/dashboard` returned `dashboard_init` with `atm=null`.
  - Filesystem evidence: `data/atm_decay` contained `atm_series_20260422.jsonl` only; no `atm_series_20260423.*` existed before RTH.
  - `npm --prefix l4_ui run test -- atmHistoryHydrate`
  - `npm --prefix l4_ui run test -- debugHotkey.integration`
  - `$env:VITE_BACKEND_ORIGIN='http://127.0.0.1:8001'; npm --prefix l4_ui run build`
  - `.\.venv\Scripts\python.exe manage.py validate-session --strict`
- Failed / Not Run:
  - No browser-side visual automation was run after the code change; user-facing confirmation still requires refreshing the currently open page.

## Pending
- Must Do Next:
  - Refresh the open browser tab and confirm the red ATM fast-fail banner disappears in premarket.
- Nice to Have:
  - If an ATM fast-fail still appears during `OPEN`, investigate backend `AtmDecayTracker` persistence separately; that would be a real runtime issue, not the L4 false positive fixed here.

## Debt Record (Mandatory)
- DEBT-EXEMPT: bounded L4 root-cause bugfix with no new debt introduced.
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-25
- DEBT-RISK: if same-day ATM history is empty during `OPEN`, the fast-fail will still surface correctly and require a backend/tracker fix.
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: none; no runtime artifacts were added to versioned sources in this session.
- OPENSPEC-EXEMPT: targeted L4 runtime guard correction on an existing cold-boot ATM contract; no new proposal chain or cross-layer schema surface was introduced.

## How To Continue
- Start Command: `.\.venv\Scripts\python.exe manage.py start-all`
- Key Logs: `logs\backend_runtime.current.log`, `logs\frontend_runtime.current.log`
- First File To Read: `notes/sessions/2026-04-23/atm-history-strict-fail/handoff.md`

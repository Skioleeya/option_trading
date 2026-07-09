# Project State

## Snapshot
- DateTime (ET): 2026-04-23 08:04:15 -04:00
- Branch: `master`
- Last Commit: `b6ef4ff6e0a7deafeb86af41746fbc1db3e48637`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: remove the false frontend ATM strict fast-fail that appears premarket when same-day ATM history is legitimately empty before RTH.
- Scope In: front-end strict hydrate gate, ATM history cold-boot semantics, L4 regression coverage, SOP sync, and session/context bookkeeping.
- Scope Out: backend ATM persistence behavior during RTH, new tracker/storage behavior, and non-ATM frontend work.

## What Changed (Latest Session)
- Files: `l4_ui/src/components/App.tsx`, `l4_ui/src/components/__tests__/atmHistoryHydrate.test.tsx`, `docs/SOP/L4_FRONTEND.md`, `notes/context/project_state.md`, `notes/context/open_tasks.md`, `notes/context/handoff.md`, and `notes/sessions/2026-04-23/atm-history-strict-fail/*`.
- Behavior: `App.tsx` now requires non-empty ATM history only during `OPEN` RTH; outside RTH, empty same-day history remains a legal `-- PENDING` state instead of surfacing `ATM HISTORY FAST-FAIL`.
- Verification: live host evidence reproduced the root cause (`/api/atm-decay/history count=0`, WS `atm=null`, no `data/atm_decay/atm_series_20260423.*` before RTH); targeted Vitest passed for both outside-RTH and RTH strict-gate behavior; frontend production build passed.

## Risks / Constraints
- Risk 1: this fix intentionally changes only the L4 gate; if ATM history is still empty during `OPEN`, the fast-fail remains by design and the root cause would be backend/tracker persistence.
- Risk 2: current live evidence was collected premarket, so it confirms the false-positive condition before RTH rather than same-day post-open persistence quality.

## Next Action
- Immediate Next Step: refresh the frontend page on `http://localhost:5173` and confirm the premarket ATM card returns to `-- PENDING` without the strict error banner.
- Owner: Codex

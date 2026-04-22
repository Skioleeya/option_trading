# Project State

## Snapshot
- DateTime (ET): 2026-03-25 09:57:49 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Trace the TradingView ATM decay chart end-to-end and determine whether call/put/straddle samples are continuously injected, normalized correctly, and incrementally rendered.
- Scope In: Frontend history hydration, websocket ATM payload flow, chart normalization/smoothing logic, incremental update planner, live browser observation, and backend ATM history/runtime evidence.
- Scope Out: Code changes or production fixes in this session.

## What Changed (Latest Session)
- Files: Session/context records only.
- Behavior: No code changed. Investigation found the chart pipeline is not currently receiving continuous live ATM samples, and persisted ATM history contains out-of-order / future-looking timestamps that poison incremental rendering semantics.
- Verification: Code-path trace completed. Direct `/ws/dashboard` sampling, headless browser observation, `/api/atm-decay/history` inspection, and backend log review all converged on the same failure pattern.

## Risks / Constraints
- Risk 1: Frontend chart can appear alive because the page still redraws and websocket heartbeats continue, but call/put/straddle curves are effectively frozen because `atm` updates are not continuously injected.
- Risk 2: Even if new live ATM points resume, the persisted history currently includes `15:01-15:02 ET` rows ahead of current `09:5x ET`, so the frontend incremental planner will fall back to `setData` rather than clean append-mode updates.

## Next Action
- Immediate Next Step: Open a repair session for ATM decay timestamp/history correctness and live ATM payload continuity.
- Owner: `Codex`

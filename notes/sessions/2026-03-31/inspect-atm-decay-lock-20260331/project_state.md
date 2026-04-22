# Project State

## Snapshot
- DateTime (ET): 2026-03-31 09:36:08 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `790471c`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Determine whether ATM decay anchor lock logic is malfunctioning in today's live runtime.
- Scope In: `l1_compute/analysis/atm_decay/*`, `app/lifespan.py`, current backend logs, `/api/atm-decay/history`, `/debug/persistence_status`, and targeted ATM decay regression tests.
- Scope Out: Implementing a lock-logic fix, frontend rendering changes, or unrelated runtime subsystems.

## What Changed (Latest Session)
- Files: `notes/context/project_state.md`, `notes/context/open_tasks.md`, `notes/context/handoff.md`, `notes/sessions/2026-03-31/inspect-atm-decay-lock-20260331/project_state.md`, `notes/sessions/2026-03-31/inspect-atm-decay-lock-20260331/open_tasks.md`, `notes/sessions/2026-03-31/inspect-atm-decay-lock-20260331/handoff.md`, `notes/sessions/2026-03-31/inspect-atm-decay-lock-20260331/meta.yaml`
- Behavior: No active lock failure was found. Before `09:30 ET`, the tracker correctly remained unlocked due to the explicit RTH gate; after the open, the tracker logged `capture stall` until liquidity converged, then locked `639` at `09:30:47 ET` and continued emitting live ATM decay points. A follow-up anomaly remains: the history stream stored a post-lock flat `0/0/0` row at `09:30:49 ET` immediately after the first valid non-zero point at `09:30:48 ET`.
- Verification: Live logs showed `capture stall: failures=30` at `09:30:34`, `ANCHOR LOCKED` at `09:30:47`, and continuous `anchor=YES` updates afterward; `/api/atm-decay/history` returned `locked_at=09:30:47` with 145 rows and continuous later samples; `/debug/persistence_status` remained healthy with `redis.connected=true`, `gateway.connected=true`, and `transport.status=OK`; targeted ATM decay tests passed (`31 passed`).

## Risks / Constraints
- Risk 1: The stored `09:30:49` flat row is not a lock failure, but it shows current suppression only covers the initial opening flat tick, not later post-lock flat points.
- Risk 2: Today's runtime did not persist any `atm_anchor_diag_20260331` diagnostic file, so the exact leg prices behind the flat row were not captured through the starvation diagnostic path.

## Next Action
- Immediate Next Step: If the flat `09:30:49` row matters, trace that tick's anchor-leg quote inputs and decide whether post-lock flat rows should also be suppressed or separately diagnosed.
- Owner: Codex

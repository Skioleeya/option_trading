# Project State

## Snapshot
- DateTime (ET): 2026-07-15 14:19 -04:00
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `df702b3`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Repair ATM decay source freshness, leg freshness, stale recovery chart breaks, and roll-anchor marker preservation.
- Scope In: app/L1 ATM update contract, ATM payload/history fields, L4 chart whitespace behavior, targeted tests, SOP/OpenSpec/session evidence.
- Scope Out: CALL/PUT color changes, market-state voting logic, broad backend Rust migration, unrelated cold data artifacts.

## What Changed (Latest Session)
- Files: app ATM freshness context, L1 ATM raw pct/freshness, L0 row timestamp update, history route, L4 chart/history types, SOP/OpenSpec/tests.
- Behavior: stale L0 source no longer emits ordinary ATM points; recovery/long gaps break L4 chart continuity; CALL/PUT legs require same freshness; `strike_changed` survives suppressed opening zero ticks.
- Verification: Rust pyd rebuild passed; targeted backend pytest passed; L4 full test suite and build passed; strict validation passed. Standard start-all was stopped by explicit user request after market close.

## Risks / Constraints
- L1 Python compute restrictions require keeping new raw pct/freshness logic out of Python numerical loops.
- Existing untracked `data/cold/20260714` artifacts predate this session and must remain untouched.

## Next Action
- Immediate Next Step: commit/push if requested; defer standard start-all evidence to next market-session/runtime check by user direction.
- Owner: Codex

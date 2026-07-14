# Project State

## Snapshot
- DateTime (ET): 2026-07-14 12:03 -04:00
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `d10e01d`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Stabilize dynamic subscription behavior by making ATM anchor legs mandatory from the compute-loop ATM update path and align local subscription cap to official 500.
- Scope In: app loop orchestration, SharedLoopState diagnostics, L0/L1 SOP, OpenSpec, targeted tests, local `.env` cap.
- Scope Out: L4 color semantics, L1 numerical compute, ActiveOptions hard-fail policy changes.

## What Changed (Latest Session)
- Files: app loop helper/callers, targeted app loop tests, L0/L1 SOP, OpenSpec change, session notes.
- Behavior: anchor symbol changes now trigger mandatory set, immediate subscription refresh, and bounded price repair from compute-loop ATM updates.
- Verification: Targeted pytest passed; strict validation passed; `start-all` reported Redis/Backend/Frontend up.

## Risks / Constraints
- `AGENTS.md` was dirty before this fix from a prior user-requested backlog reminder and is preserved.
- Local `.env` changed `SUBSCRIPTION_MAX=500`; `.env` is not tracked and must not be committed.

## Next Action
- Immediate Next Step: Commit and push the validated change set.
- Owner: Codex

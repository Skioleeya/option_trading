# Project State

## Snapshot
- DateTime (ET): 2026-03-06 16:47:25 -05:00
- Branch: `master`
- Last Commit: `cc48066`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `PARTIAL` (process/tooling session; runtime e2e not executed)

## Current Focus
- Primary Goal: Add zero-technical-debt governance contract and enforce it in session validation gate.
- Scope In:
  - `AGENTS.md`
  - `scripts/validate_session.ps1`
  - `notes/sessions/_templates/handoff.template.md`
  - `notes/sessions/_templates/open_tasks.template.md`
  - `TECH_DEBT_TASKLIST.md` (root debt execution list)
  - Session/context notes for current active pointer
- Scope Out:
  - Trading model/runtime logic changes
  - Frontend behavior changes

## What Changed (Latest Session)
- Files:
  - `AGENTS.md`
  - `scripts/validate_session.ps1`
  - `notes/sessions/_templates/handoff.template.md`
  - `notes/sessions/_templates/open_tasks.template.md`
  - `TECH_DEBT_TASKLIST.md`
- Behavior:
  - Added mandatory Section 8 debt contract in AGENTS.
  - Validator now enforces debt-exempt fields, SLA due windows, debt metrics arithmetic, and duplicate unresolved debt scan.
  - Handoff/open_tasks templates now include debt record and supersede marker guidance.
  - Added root-level net debt execution list with recommended reprioritization (`P0/P1/P2/ignore`).
- Verification:
  - `./scripts/validate_session.ps1` (passed)

## Risks / Constraints
- Risk 1: Debt gate is strict; legacy sessions may require structured debt fields if validated as active.
- Risk 2: Duplicate-debt detection is exact-text based (semantic duplicates still require human review).

## Next Action
- Immediate Next Step: Execute P0 debt items from `TECH_DEBT_TASKLIST.md` in a dedicated delivery session.
- Owner: Codex / next agent

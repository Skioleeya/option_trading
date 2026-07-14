# Startup: fix-dynamic-subscription-anchor-mandatory

STARTUP-PROOF: Created dedicated session with `python manage.py new-session --task-id fix-dynamic-subscription-anchor-mandatory`; read context indexes, prior ATM decay handoff, SOP fast-load pack, and current git state before runtime edits.

## Session
- Path: `notes/sessions/2026-07-14/fix-dynamic-subscription-anchor-mandatory/`
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Base commit: `d10e01d`

## Scope Understanding
- In scope: dynamic subscription stability, ATM anchor mandatory sync independence, local `SUBSCRIPTION_MAX=500`, targeted tests, OpenSpec, SOP, session evidence.
- Out of scope: L4 color remapping, L1 numerical compute, broker-side market prediction logic.

## Prior Context Read
- `notes/context/project_state.md`
- `notes/context/open_tasks.md`
- `notes/context/handoff.md`
- `notes/sessions/2026-07-13/debug-atm-decay-frontend-spike/*`
- `docs/SOP/SYSTEM_OVERVIEW.md`
- `docs/SOP/L0_DATA_FEED.md`
- `docs/SOP/L1_LOCAL_COMPUTATION.md`
- `docs/SOP/L2_DECISION_ANALYSIS.md`
- `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- `docs/SOP/L4_FRONTEND.md`
- `openspec/AGENTS.md`

## Recent Git Context
- Key commits reviewed: `d10e01d`, `acb92bd`, `36a51af`, `dd7d189`, `645f2d3`.
- Current dirty file before this fix: `AGENTS.md` contained the user-requested full-Rust backend backlog reminder.

## Worker Readiness
- Risks noticed: `app/loops/compute_loop.py` was already near the 400-line ceiling, so behavior had to live in a new focused helper.
- Blockers noticed: N/A:no external blocker found.

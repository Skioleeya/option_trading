# Startup: fix-atm-decay-freshness-breaks

STARTUP-PROOF: notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/startup.md

## Session
- Session ID: 2026-07-15/fix-atm-decay-freshness-breaks
- Started ET: 2026-07-15 14:18:24 -04:00
- Branch: codex/research-persistence-startup-fixes-20260423
- Base commit: df702b3

## Scope Understanding
- In scope: ATM decay source freshness gate, CALL/PUT leg freshness validation, payload/history field extension, L4 whitespace breaks, strike_changed preservation after roll anchor.
- Out of scope: L4 CALL/PUT color remapping, market-state voting work, broader backend Rust rewrite, unrelated cold data artifacts.

## Prior Context Read
- notes/context/project_state.md
- notes/context/open_tasks.md
- notes/context/handoff.md
- notes/sessions/2026-07-14/fix-dynamic-subscription-anchor-mandatory/*
- docs/SOP/SYSTEM_OVERVIEW.md
- docs/SOP/L0_DATA_FEED.md
- docs/SOP/L1_LOCAL_COMPUTATION.md
- docs/SOP/L2_DECISION_ANALYSIS.md
- docs/SOP/L3_OUTPUT_ASSEMBLY.md
- docs/SOP/L4_FRONTEND.md
- openspec/changes/impl-20260714-anchor-mandatory-subscription-stability/*

## Recent Git Context
- Key commits reviewed: df702b3
- Dirty context before edits: untracked data/cold 20260714 artifacts existed before this session and are preserved.

## Worker Readiness
- Risks noticed: L1 Python compute restrictions require avoiding new Python numerical compute in ATM raw pct logic.
- Blockers noticed: `new-session --update-pointer` hit PermissionError while updating notes/context/project_state.md; session-local files were created and context sync will be retried at handoff.

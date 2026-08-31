# Startup: gex-l0-l4-audit

STARTUP-PROOF: Read AGENTS directive from user prompt; loaded notes-session-records skill; read notes/context project_state/open_tasks/handoff; read active session project_state/open_tasks/handoff/meta; read SOP fast-load pack; ran git status and targeted GEX code searches.

## Session
- Session path: notes/sessions/2026-07-16/gex-l0-l4-audit/
- DateTime (ET): 2026-07-16 09:48 -04:00
- Branch: codex/research-persistence-startup-fixes-20260423
- Head commit: d89a877

## Scope Understanding
- In scope: Read-only L0-L4 GEX business logic audit, formula/unit/sign verification, runtime payload sampling, and targeted regression evidence.
- Out of scope: Runtime code changes, broker restart, standard start-all evidence, OpenSpec implementation proposal.

## Prior Context Read
- notes/context/project_state.md
- notes/context/open_tasks.md
- notes/context/handoff.md
- notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/project_state.md
- notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/open_tasks.md
- notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/handoff.md
- notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/meta.yaml
- docs/SOP/SYSTEM_OVERVIEW.md
- docs/SOP/L0_DATA_FEED.md
- docs/SOP/L1_LOCAL_COMPUTATION.md
- docs/SOP/L2_DECISION_ANALYSIS.md
- docs/SOP/L3_OUTPUT_ASSEMBLY.md
- docs/SOP/L4_FRONTEND.md

## Recent Git Context
- Key commits reviewed: d89a877 current HEAD.
- Git status at startup: branch aligned with origin; new session notes untracked after session creation.

## Worker Readiness
- Risks noticed: L3 catches MicroStats presenter exceptions and zero-states the card, which can mask invalid gex_regime despite the SOP fail-fast contract.
- Blockers noticed: Playwright is not installed in the active .venv, so UI browser reconciliation script cannot run without dependency install; no code change was needed for the audit.

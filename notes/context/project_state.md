# Project State

## Active Session
- Path: notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/project_state.md
- Meta: notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/meta.yaml
- Status: ACTIVE

ACTIVE_SESSION: notes/sessions/2026-07-15/fix-atm-decay-freshness-breaks/project_state.md
LAST_UPDATED: 2026-07-15 16:09 -04:00
ARCHIVE: notes/context/archive/project_state_2026-07.md

CURRENT_STATE:
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Focus: ATM decay source freshness, leg freshness, stale recovery chart breaks, and strike_changed preservation.
- Status: Implementation complete; targeted backend pytest, Rust pyd rebuild, L4 tests/build, and strict validation passed. Standard start-all was stopped by explicit user request after market close.

NEXT:
- Commit/push if requested.
- Defer standard `python manage.py start-all` evidence to the next requested runtime window.

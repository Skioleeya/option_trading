# Open Tasks

## Priority Queue
- [x] P0: Complete Sub-wave D assessment document
  - Owner: Codex
  - Definition of Done: `redis_service.py`, `historical_store.py`, `tactical_triad_logic.py` all have explicit consumer map + decision + trigger in OpenSpec assessment.
  - Blocking: None
- [x] P1: SOP retention documentation for Python-owned utilities
  - Owner: Codex
  - Definition of Done: `docs/SOP/SYSTEM_OVERVIEW.md` records consumers, defer reasons, and migration triggers for retained `shared/system` utilities.
  - Blocking: None
- [x] P2: Strict validation and handoff synchronization
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and session/context files are synchronized.
  - Blocking: None

## Parking Lot
- [ ] Evaluate tactical-triad wrapper deletion after `shared_rust.services` namespace collapse.
- [ ] Revisit redis/historical owner migration only when app-level infra ownership changes.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Sub-wave D storage/utility assessment finalized with explicit per-consumer decisions (2026-04-02 ET)

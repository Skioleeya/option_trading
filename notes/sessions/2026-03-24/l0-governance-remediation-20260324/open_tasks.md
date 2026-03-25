# Open Tasks

## Priority Queue
- [x] P0: Reconcile L0 runtime subscribe semantics with the active Rust session
  - Owner: Codex
  - Definition of Done: `subscribe()` applies the full desired set to the active runtime session and diagnostics expose applied vs desired state.
  - Blocking: None
- [x] P0: Centralize L0 normalization and metadata resolution
  - Owner: Codex
  - Definition of Done: Tier1/Tier2/Tier3 stop duplicating IV/OI parsing and metadata scan/build logic.
  - Blocking: None
- [x] P0: Clean snapshot projection contract and source-time semantics
  - Owner: Codex
  - Definition of Done: `aggregate_greeks/ttm_seconds` are absent from L0 payload and `as_of/as_of_utc` bind to L0 source update time.
  - Blocking: None
- [x] P0: Pass strict session validation with OpenSpec/SOP/session records synced
  - Owner: Codex
  - Definition of Done: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` returns PASS.
  - Blocking: None

## Parking Lot
- [ ] Item: Consider splitting `quote_runtime.py` further if subsequent governance work pushes it close to the 400-line ceiling.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Rust runtime subscribe now reconciles active session symbols instead of Python-only tracking (2026-03-24 22:23 ET)
- [x] Shared metadata resolver adopted by `SubscriptionManager` / Tier2 / Tier3 (2026-03-24 22:26 ET)
- [x] Shared sanitizer-backed IV/OI parsing wired into sync and pollers (2026-03-24 22:27 ET)
- [x] L0 snapshot projection rebound to source time and legacy payload fields removed (2026-03-24 22:28 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/v2` passed with `71 passed` (2026-03-24 22:29 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed (2026-03-24 22:35 ET)

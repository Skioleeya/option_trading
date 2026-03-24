# Open Tasks

## Priority Queue
- [ ] P0: Pass strict session validation for the L0 ingest structure-governance change set
  - Owner: Codex
  - Definition of Done: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` returns PASS with session/context/OpenSpec gates green.
  - Blocking: None
- [ ] P1: Confirm no runtime imports remain on `l0_ingest.feeds.*` or `l0_ingest.subscription_manager`
  - Owner: Codex
  - Definition of Done: repo scan is clean except historical notes/OpenSpec prose.
  - Blocking: None
- [ ] P2: Decide whether non-runtime legacy directories (`events/`, `sanitize/`, `store/`, `quality/`, `observability/`) need a later namespace convergence pass
  - Owner: Codex
  - Definition of Done: explicit follow-up decision recorded or debt closed.
  - Blocking: Out of scope for this session

## Parking Lot
- [ ] Audit whether `l0_ingest/l0_rust.py` should remain a top-level compatibility shim or move under a later runtime namespace cleanup.
- [ ] Consider adding a lightweight package-boundary test that imports every `l0_ingest.v2` public subpackage once.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Removed flat `l0_ingest/feeds/*` runtime tree by relocating modules into hierarchical `l0_ingest/v2/*` subpackages (2026-03-24 12:55 ET)
- [x] Moved V2 runtime tests into `l0_ingest/tests/v2/*` and rewired imports (2026-03-24 12:59 ET)
- [x] Updated L0 README/SOP docs and added structure-governance OpenSpec record (2026-03-24 13:02 ET)

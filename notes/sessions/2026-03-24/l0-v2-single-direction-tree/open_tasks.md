# Open Tasks

## Priority Queue
- [ ] P2: Retire or quarantine legacy `l0_ingest/feeds/option_chain_builder.py` so future work cannot drift back to the old path
  - Owner: Codex
  - Definition of Done: Legacy builder is clearly marked non-primary or removed under a dedicated cleanup session.
  - Blocking: Out of scope for this hard-cut session

## Parking Lot
- [ ] Add dedicated unit tests for `l0_ingest/v2/facade.py` startup/uninitialized/error snapshot paths.
- [ ] If Rust toolchain permits later, run cargo-level validation for `l0_ingest/l0_rust`.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Built `l0_ingest/v2` single-direction worktree and cut app wiring to the new facade (2026-03-24 12:20 ET)
- [x] Moved Arrow schema and Rust SHM bridge to shared neutral modules (2026-03-24 12:16 ET)
- [x] Removed Active Options adapter fallback to L0 legacy Greeks/TTM fields (2026-03-24 12:20 ET)
- [x] Split `l0_ingest/l0_rust/src/lib.rs` under the file-length gate (2026-03-24 12:27 ET)
- [x] Passed `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` after fixing OpenSpec chain issues (2026-03-24 12:31 ET)

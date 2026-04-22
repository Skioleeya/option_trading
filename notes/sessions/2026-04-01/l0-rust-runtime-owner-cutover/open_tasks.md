# Open Tasks

## Priority Queue
- [ ] P1: move startup/bootstrap helpers from Python into a narrower Rust-native owner
  - Owner: Codex
  - Definition of Done:
    - `sdk_bootstrap.py` no longer owns runtime-critical bootstrap semantics
    - startup probe and endpoint normalization have a Rust-native or neutral contract owner
  - Blocking: separate implementation slice after runtime-owner cutover
- [ ] P2: retire or modernize `LongportFeedAdapter`
  - Owner: Codex
  - Definition of Done:
    - legacy adapter either targets the Rust-only runtime contract or is explicitly removed
  - Blocking: no live-path blocker; currently stub-only

## Parking Lot
- [ ] evaluate whether direct Python import of generated `.pyd` can be documented more explicitly for local developer workflows
- [ ] review whether `sdk_bootstrap.py` should be split further to keep bootstrap contracts isolated from diagnostics wrappers

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Removed `PythonQuoteRuntime`, Python `QuoteContext` owner files, and the old `l0_rust` shim consumption path (2026-04-01 13:01 ET)

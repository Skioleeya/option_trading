# Open Tasks

## Priority Queue
- [x] P0: cut runtime consumers over to root-neutral `shared.services` ActiveOptions surfaces
  - Owner: Codex
  - Definition of Done: app/l2/l3 runtime imports no longer reference package-internal `shared.services.active_options.*` modules
  - Blocking: none
- [ ] P1: replace root-neutral wrappers with Rust-backed ActiveOptions owners
  - Owner: Codex
  - Definition of Done: `ActiveOptionsRuntimeService` and input-adapter public surfaces resolve from Rust-backed implementations
  - Blocking: import-surface cutover complete
- [ ] P2: delete `shared/services/active_options/*` package internals and relocate tests
  - Owner: Codex
  - Definition of Done: package-internal runtime imports reach zero and the package tree is removed or reduced to non-runtime artifacts only
  - Blocking: Rust-backed owners must land first

## Parking Lot
- [ ] Update SOP once the Rust-backed owner replacement changes the final public import surface.
- [ ] Fold the temporary root-neutral wrappers away after package retirement.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wrote migration-stability governance into `AGENTS.md`: prefer minimum transitional files and reject wrapper fan-out during cutover (2026-04-02 06:47 ET)
- [x] Runtime consumer imports now resolve through root-neutral `shared.services` ActiveOptions surfaces (2026-04-02 06:25 ET)

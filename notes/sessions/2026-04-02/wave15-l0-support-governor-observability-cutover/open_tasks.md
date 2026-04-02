# Open Tasks

## Priority Queue
- [ ] P1: Continue `shared/services` cutover with the next owner group.
  - Owner: Codex
  - Definition of Done: Execute the next bounded cluster after `l0_support`, update SOP/evidence, and pass strict validation.
  - Blocking: None
- [ ] P1: Consolidate temporary Rust-only module names under the final `shared_rust.services` namespace.
  - Owner: Codex
  - Definition of Done: Replace temporary module names such as `shared_rust.services_root` / `services_l0_support` with the stable `shared_rust.services.*` layout without reintroducing Python facades.
  - Blocking: Current `.pyd` naming/layout split
- [ ] P2: Remove stale `__pycache__` directories under retired `shared/services/l0_support` subtrees when safe.
  - Owner: Codex
  - Definition of Done: Obsolete cache directories are cleaned in a dedicated cleanup slice.
  - Blocking: Destructive filesystem cleanup must stay out of this runtime-focused session

## Parking Lot
- [ ] Revisit `shared/services` root namespace consolidation once more owner groups are Rust-only.
- [ ] Audit remaining `shared/services` tests for package-local import assumptions after future cutovers.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Cut over `shared/services/l0_support/rate_governor/*` and `observability/*` to `shared_rust.services_l0_support` and removed the old Python owners (2026-04-02 03:40 ET)

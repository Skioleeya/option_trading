# Open Tasks

## Priority Queue
- [x] P0: finish Wave 18 in one session without splitting P1 and P2
  - Owner: Codex
  - Definition of Done: Rust-backed ActiveOptions owner lands behind the root-neutral surfaces and the transient helper layer is removed in the same session
  - Blocking: none
- [x] P1: replace root-neutral wrappers with Rust-backed ActiveOptions owners
  - Owner: Codex
  - Definition of Done: `shared/services/active_options_runtime.py`, `shared/services/active_options_input.py`, and `shared/services/active_options_engines.py` resolve to `shared_rust.services`
  - Blocking: none
- [x] P2: delete transient ActiveOptions Python helper owners
  - Owner: Codex
  - Definition of Done: `_active_options_*` helper files are removed and the remaining neutral surfaces become the only Python blast-radius limiter
  - Blocking: P1 landed in the same session

## Parking Lot
- [ ] Fold the root-neutral ActiveOptions Python surfaces away only when import-site churn is acceptable and `shared_rust.services` can become the direct public entrypoint.
- [ ] Fix the local ACL on `tmp/pytest_cache`.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Rust-backed ActiveOptions service/input/engine owner landed behind the root-neutral surfaces (2026-04-02 08:10 ET)
- [x] Deleted the transient `_active_options_*` Python helper layer in the same session as the owner cutover (2026-04-02 08:10 ET)

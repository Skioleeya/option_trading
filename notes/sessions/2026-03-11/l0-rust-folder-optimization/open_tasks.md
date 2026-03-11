# Open Tasks

## Priority Queue
- [ ] P0: SUPERSEDED-BY: 2026-03-11/agents-new-session-pointer-policy
  - Owner: N/A
  - Definition of Done: N/A
  - Blocking: None
- [ ] P1: SUPERSEDED-BY: 2026-03-11/agents-new-session-pointer-policy
  - Owner: N/A
  - Definition of Done: N/A
  - Blocking: None
- [ ] P2: SUPERSEDED-BY: 2026-03-11/agents-new-session-pointer-policy
  - Owner: N/A
  - Definition of Done: N/A
  - Blocking: None

## Parking Lot
- [ ] Validate whether any packaging/deploy script assumes package directory `l0_rust/`.
- [ ] Add a regression that asserts `from l0_ingest import l0_rust` resolves `l0_ingest/_native/l0_rust.pyd`.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Move binary into L0 layer (`l0_ingest/_native/l0_rust.pyd`) and align imports to `from l0_ingest import l0_rust` (2026-03-11 ET)

# Open Tasks

## Priority Queue
- [ ] P1: Decide whether to open a separate session for the unrelated `ArrowIpcReader.close(): Already borrowed` shutdown bug exposed during real-host restart verification. SUPERSEDED-BY: 2026-04-21/arrow-ipc-close-borrow-fix
  - Owner: Codex / operator
  - Definition of Done: either a new session is opened for that bug, or the team explicitly defers it with owner and due date outside this session.
  - Blocking: none.
- [ ] P2: Consider a dedicated startup-replay metric in diagnostics (`recovered_label_rows_on_startup`) if operations needs explicit observability for recovered cohorts.
  - Owner: Codex
  - Definition of Done: either add the metric in a follow-up session or explicitly reject it as unnecessary.
  - Blocking: none.

## Parking Lot
- [ ] Evaluate whether startup replay should scan more than the latest feature day for historical post-close recoveries.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Replaced pure in-memory `pending_labels` ownership with deterministic startup replay from persisted feature/label tiers (2026-04-21 17:57 ET).
- [x] Recovered 20260421 label continuity on real host (`3265 -> 14386` rows) and reran archive/classification to `quality=PASS` with synchronized manifests (2026-04-21 17:57 ET).

# Open Tasks

## Priority Queue
- [x] P0: Create and register the follow-up OpenSpec parent/child family for residual `formula-semantic` work.
  - Owner: Codex
  - Definition of Done: `openspec list` shows `formula-semantic-followup-parent-governance` plus children `phase-e/f/g/h`.
  - Blocking: None.
- [ ] P1: Decide whether to keep or discard the partial runtime edits that were started before scope was narrowed to proposal-first.
  - Owner: Codex / next implementing agent
  - Definition of Done: Each touched runtime file is either validated and linked to the new proposals or explicitly reverted in a controlled follow-up session.
  - Blocking: Requires review against the newly created proposal family and current user intent.
- [ ] P1: Continue with child `Phase E` implementation only after proposal-first checkpoint is accepted.
  - Owner: Codex / next implementing agent
  - Definition of Done: provenance registry, proxy labels, and docstring/SOP updates are implemented and tested.
  - Blocking: Current session stops at proposal creation and handoff preparation.
- [ ] P2: Reconcile old `formula-semantic-*` proposal task state after runtime follow-up work lands.
  - Owner: Codex / next implementing agent
  - Definition of Done: old A/B/D tasks are backfilled, old `Phase C` is marked handed off to new `Phase E`, and parent governance reflects the residual transfer.
  - Blocking: Depends on later child completion.

## Parking Lot
- [ ] Decide whether `guard_vrp_proxy_pct` should live in `shared/contracts/metric_semantics.py` only or also receive a dedicated helper module for guard-specific normalization.
- [ ] Decide whether `net_vanna_raw_sum` needs any L3/L4 debug surfacing or remains research/debug only.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Created the new follow-up OpenSpec family and confirmed visibility via `openspec list` (2026-03-13 09:01:34 -04:00)

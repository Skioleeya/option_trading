# Open Tasks

## Priority Queue
- [x] P0: Author the OpenSpec proposal for a non-overlapping day taxonomy.
  - Owner: Codex
  - Definition of Done: `proposal.md`, `design.md`, `tasks.md`, and `specs/.../spec.md` define a literature-backed taxonomy with exclusive primary labels and orthogonal modifiers.
  - Blocking: None.
- [ ] P1: Validate the proposal session and sync final context metadata.
- [x] P1: Validate the proposal session and sync final context metadata.
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and session/context notes reflect the final proposal summary.
  - Blocking: None.
- [ ] P2: Convert the approved taxonomy proposal into an implementation plan for `scripts/diagnostics/eod_bucket_*`.
  - Owner: Codex
  - Definition of Done: Execution session created with threshold design, legacy compatibility plan, and sample-day replay list.
  - Blocking: Proposal review/approval.

## Parking Lot
- [ ] Decide whether canonical naming should migrate `range_day` to `balance_day` immediately or via one compatibility release.
- [ ] Decide whether `close_profile` should be archived in manifest/quality output in phase 1 or added after the primary taxonomy cutover.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Reviewed literature on regime/state labeling and intraday reversal/pinning semantics. (2026-03-31 01:20 ET)
- [x] Drafted OpenSpec change `research-day-taxonomy-non-overlap-20260331`. (2026-03-31 01:32 ET)
- [x] Strict session validation passed. (2026-03-31 01:34 ET)

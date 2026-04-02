# Open Tasks

## Priority Queue
- [ ] P1: Verify the next regular-hours post-lock flat ATM decay write produces a `flat_post_lock_row` diagnostic with concrete call/put leg quotes.
  - Owner: Codex
  - Definition of Done: Capture either Redis `app:atm_anchor_diag:<YYYYMMDD>` or cold JSONL evidence showing the flat row's call/put `bid/ask/last/mid` snapshot and correlate it to the stored `0/0/0` row timestamp.
  - Blocking: Requires a fresh live reproduction during market hours.
- [ ] P2: Decide whether post-lock flat rows should remain persisted, be suppressed, or only be surfaced with degraded-state tagging after live evidence is captured.
  - Owner: Codex
  - Definition of Done: Root-cause evidence exists and the intended product semantics for flat post-lock rows are explicitly chosen.
  - Blocking: Depends on the P1 diagnostic capture above.

## Parking Lot
- [ ] If repeated flat-row diagnostics show quote churn or snapshot race rather than real price convergence, consider adding a lightweight `snapshot_version` or source marker into the diagnostic payload.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added `flat_post_lock_row` tracker diagnostics plus focused regression tests. (2026-03-31 09:45 ET)

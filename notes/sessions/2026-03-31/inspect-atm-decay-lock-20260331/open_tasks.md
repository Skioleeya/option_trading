# Open Tasks

## Priority Queue
- [x] P0: Determine whether today's ATM decay lock logic is failing to acquire or retain an anchor.
  - Owner: Codex
  - Definition of Done: Live runtime evidence and targeted tests show whether the lock path is broken or healthy.
  - Blocking: None.
- [x] P1: Run the lock/restore/recovery regression set for ATM decay.
  - Owner: Codex
  - Definition of Done: `test_atm_decay_tracker.py`, `test_atm_decay_anchor_recovery.py`, and `test_atm_decay_modular.py` all pass.
  - Blocking: None.
- [ ] P1: Trace why a post-lock flat `0/0/0` ATM row was stored at `2026-03-31 09:30:49 ET` immediately after the first valid non-zero sample.
  - Owner: Codex
  - Definition of Done: Confirm whether the flat row came from legitimate quote reversion to anchor prices or from a logic gap that should be suppressed/diagnosed separately.
  - Blocking: Current diagnostics capture starvation legs, but not successful flat post-lock rows.

## Parking Lot
- [ ] Decide whether successful flat post-lock rows need dedicated forensic diagnostics similar to `raw_pct_unavailable`.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Verified that the tracker intentionally stays unlocked before `09:30 ET`; the earlier `anchor=NO` state was expected, not a fault. (2026-03-31 09:33 ET)
- [x] Confirmed today's live anchor locked at `09:30:47 ET` on strike `639` and has remained active through subsequent updates. (2026-03-31 09:34 ET)
- [x] Ran targeted ATM decay regression tests: `31 passed`. (2026-03-31 09:34 ET)

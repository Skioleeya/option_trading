# Open Tasks

## Priority Queue
- [ ] P2: Re-run the same 60-second validation during market hours and compare version cadence, contract population, and warm-up pressure against the after-hours profile.
  - Owner: Codex
  - Definition of Done: Capture one market-hours JSON artifact and summarize the differences versus `tmp/l0_l1_live_flow_validation_60s.json`.
  - Blocking: Requires an open-market verification window with live provider connectivity.

## Parking Lot
- [ ] Consider whether the IV warm-up observed `301607` path warrants a dedicated governor/telemetry review session if it starts impacting live continuity rather than remaining a handled diagnostic.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Executed `scripts/test/l0_l1_live_flow_validation_60s.py` for 60 seconds with an escalated live run and recorded `classification=LIVE` at 2026-03-24 22:56:03 -04:00.
- [x] Confirmed the sandboxed failure was environmental rather than a L0/L1 contract or runtime defect at 2026-03-24 22:54:22 -04:00.

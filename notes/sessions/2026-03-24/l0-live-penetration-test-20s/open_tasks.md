# Open Tasks

## Priority Queue
- [ ] P1: Trace the source of implausible WS `current_volume` values observed during the 2026-03-24 after-hours live penetration run.
  - Owner: Codex
  - Definition of Done: Reproduce or explain the provider/runtime path that produced `3.6172879350397215e+18`, document whether the issue is upstream payload quality or local decode/layout mismatch, and confirm the current guard remains correct.
  - Blocking: Requires a second live feed capture window and targeted inspection of raw payload or Rust bridge decode path.

## Parking Lot
- [ ] Add a market-open variant of the penetration script that records more granular cadence/latency metrics once the 20-second smoke path is stable.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added `scripts/test/l0_live_penetration_20s.py` and executed a 20-second live L0 penetration test with JSON output (`LIVE`) at 2026-03-24 22:43:54 -04:00.

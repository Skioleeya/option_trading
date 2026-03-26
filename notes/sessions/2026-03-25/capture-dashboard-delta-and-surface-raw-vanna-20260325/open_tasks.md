# Open Tasks

## Priority Queue
- [x] P0: capture live `dashboard_delta` cadence and classify heartbeat-only vs metric-refresh frames.
  - Owner: Codex
  - Definition of Done: consecutive live frames recorded with concrete evidence for `micro_structure`, `tactical_triad`, `active_options`, `net_gex`, and heartbeat-only deltas.
  - Blocking: none
- [x] P0: surface `net_vanna_raw_sum` to L4 as a dedicated diagnostic card without expanding presenter-owned contracts.
  - Owner: Codex
  - Definition of Done: L3 payload exposes canonical raw vanna through existing `micro_structure` channel and Right Panel renders a stable card from that data.
  - Blocking: none
- [ ] P1: verify raw-vanna card cadence again during regular-hours source activity to compare heartbeat ratio against after-hours behavior.
  - Owner: Codex
  - Definition of Done: capture a regular-hours live frame window and confirm whether raw-vanna / net-gex deltas advance at trading cadence.
  - Blocking: requires market-hours source activity

## Parking Lot
- [ ] Optional: add a small frontend debug marker for “heartbeat-only delta” if operators need visual transport-vs-metric separation.
- [ ] Optional: evaluate whether raw vanna also belongs in a center/left debug overlay once more canonical raw-Greek cards are requested.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Raw vanna surfaced through live L3/L4 diagnostic chain (2026-03-25 23:17 ET)
- [x] Dashboard delta heartbeat-vs-metric refresh behavior captured from live backend (2026-03-25 23:17 ET)

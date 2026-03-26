# Open Tasks

## Priority Queue
- [x] P0: confirm whether `DepthProfile` is effectively transmitted through the live websocket payload.
  - Owner: Codex
  - Definition of Done: live capture shows concrete `depth_profile` rows in `dashboard_init` and subsequent refresh frames.
  - Blocking: none
- [x] P0: identify why TradingView ATM `call/put/straddle` live payload is missing after hours.
  - Owner: Codex
  - Definition of Done: root cause identified with evidence at the producing boundary, not guessed from the UI symptom.
  - Blocking: none
- [x] P0: add explicit payload debug markers for Depth Profile and ATM status.
  - Owner: Codex
  - Definition of Done: backend logs and frontend hydrate path both emit stable debug markers.
  - Blocking: none
- [ ] P1: verify regular-hours live `atm` payload continuity with the new debug markers enabled.
  - Owner: Codex
  - Definition of Done: capture in-hours `atm` updates or `atm` deltas with non-null `call_pct/put_pct/straddle_pct`.
  - Blocking: requires regular-hours source activity

## Parking Lot
- [ ] Optional: expose current ATM payload status in `/debug/persistence_status` if operators want an HTTP-only diagnostic path.
- [ ] Optional: add a browser-visible debug badge for heartbeat-only vs metric-refresh payloads.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Root-caused after-hours ATM null payload to the tracker regular-hours gate, not transport loss (2026-03-25 23:30 ET)
- [x] Added `[L3-PAYLOAD]` and `[L4 ATM]` explicit observability markers (2026-03-25 23:32 ET)

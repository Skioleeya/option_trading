# Open Tasks

## Priority Queue
- [ ] P1: Continue tracing why the 2026-03-24 anchor at `11:55:46 ET` never materialized a persisted ATM decay series row.
  - Owner: Codex
  - Definition of Done: `data/atm_decay/atm_series_20260324.jsonl` or Redis `app:atm_decay_series:20260324` contains at least one valid row after anchor capture, `/api/atm-decay/history` returns `count>0`, and the frontend overlay no longer stays `-- PENDING`.
  - Blocking: Requires a market-hours or immediate-after-close observation window where the first post-lock sample path can be traced live.
- [ ] P2: Decide whether the after-hours UI should explicitly show a stale-history state when an anchor exists but no ATM series is available.
  - Owner: Codex
  - Definition of Done: Product/runtime behavior is explicit: either keep `-- PENDING` intentionally with documentation, or expose a distinct "stale/no-series" fallback state.
  - Blocking: Depends on confirming whether missing series is a bug or accepted operating mode.

## Parking Lot
- [ ] Re-run the same harness with a non-empty same-day ATM series to confirm the chart can render history after hours even when live ATM ticks are gated off.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added `scripts/test/atm_decay_frontend_live_validation_60s.py` to capture ATM history API, WS ATM payloads, and TradingView page state in one 60-second harness (2026-03-24 23:11 ET).
- [x] Reproduced the current after-hours ATM `NO_DATA` state: history `count=0`, WebSocket `atm=null`, frontend canvas present, overlay `-- PENDING` for all 60 samples (2026-03-24 23:14 ET).

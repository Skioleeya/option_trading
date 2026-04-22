# Open Tasks

## Priority Queue
- [x] P0: propagate quote-lane cadence independently of live spot updates. (2026-04-21 21:57 ET)
  - Owner: Codex
  - Definition of Done: flat-price raw source arrivals update `governor_telemetry.quote_lane` and bump payload epoch without changing `spot/version`.
  - Blocking: none
- [x] P1: replace stale spot REST repair with raw-source stale fast-fail. (2026-04-21 21:57 ET)
  - Owner: Codex
  - Definition of Done: source age `>10s` skips header aux, subscription refresh, and research; recovery resumes on next raw source arrival.
  - Blocking: none
- [x] P2: preflight all EOD publish targets before first rename. (2026-04-21 21:57 ET)
  - Owner: Codex
  - Definition of Done: any existing `daily/by_regime/report` target aborts run before any final path becomes visible.
  - Blocking: none
- [x] P0: remove startup deadlock discovered during host verification without restoring stale-spot REST fallback. (2026-04-21 22:28 ET)
  - Owner: Codex
  - Definition of Done: bootstrap can reach writer-ready before the first raw source timestamp exists, and stale-gate still blocks spot-dependent work once bootstrap is complete.
  - Blocking: none
- [x] P1: stop ActiveOptions bridge from crashing on `empty_snapshot.chain=None`. (2026-04-21 22:28 ET)
  - Owner: Codex
  - Definition of Done: `_publish_active_options_input()` accepts `EnrichedSnapshot` objects whose `chain` attribute is explicitly `None` and still produces a valid merged input from L0 rows.
  - Blocking: none
- [x] P2: keep `start-all` frontend listener alive after the startup command exits. (2026-04-21 22:28 ET)
  - Owner: Codex
  - Definition of Done: host-side `python3 manage.py start-all --verify-only` reports `Frontend 5173: True` after `start-all` returns, and Windows `http://localhost:5173` responds.
  - Blocking: none

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added targeted regressions for quote-lane telemetry-only overlay, stale-source gate recovery, and EOD conflict-path preflight. (2026-04-21 21:57 ET)
- [x] Added targeted regressions for bootstrap stale-gate recovery, `chain=None` active-options input normalization, and detached frontend startup persistence. (2026-04-21 22:28 ET)

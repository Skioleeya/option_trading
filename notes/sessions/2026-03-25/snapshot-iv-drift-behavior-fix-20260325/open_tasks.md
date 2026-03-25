# Open Tasks

## Priority Queue
- [x] P0: Split the overgrown compute-loop helpers/probe out of `app/loops/compute_loop.py`.
  - Owner: Codex
  - Definition of Done: The compute loop stays orchestration-only and every touched Python file remains at or below 400 lines.
  - Blocking: None
- [x] P1: Make `snapshot_version_iv_probe` cadence-aware for `rest` ATM IV and safe across ATM/source switches.
  - Owner: Codex
  - Definition of Done: Stable `rest` ATM IV no longer accumulates drift; probe resets when `atm_symbol` or `iv_source` changes; targeted tests prove the new semantics.
  - Blocking: None
- [x] P2: Restart backend and verify the new probe diagnostics online.
  - Owner: Codex
  - Definition of Done: `/debug/persistence_status` exposes `last_atm_symbol/last_iv_source/suppressed_reason`, and live `rest` ATM IV remains non-drifting while versions advance.
  - Blocking: None

## Parking Lot
- [ ] Validate the probe on a fast-cadence `ws` ATM IV session before broadening source suppression beyond `rest`.
- [ ] Revisit whether `suppressed_reason` should prefer the cadence label over the symbol-reset label when both are true on the same tick.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Refactored compute-loop helper/probe logic into focused modules. (2026-03-25 09:31:00 ET)
- [x] Added cadence-aware probe suppression and context-reset tests. (2026-03-25 09:33:10 ET)
- [x] Restarted backend and verified live probe diagnostics on `/debug/persistence_status`. (2026-03-25 09:37:01 ET)

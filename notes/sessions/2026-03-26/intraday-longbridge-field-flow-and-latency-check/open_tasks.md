# Open Tasks

## Priority Queue
- [x] P0: verify intraday Longbridge runtime freshness across L0 ingest, L1 compute, and L3 payload continuity.
  - Owner: Codex
  - Definition of Done: `/debug/persistence_status`, websocket payload, and backend logs all show advancing versions/timestamps with `rust_started=true` and `transport.status=OK`.
  - Blocking: none
- [x] P0: verify root-level ATM payload and ATM history continue to advance during regular hours.
  - Owner: Codex
  - Definition of Done: websocket root `atm` is non-null and `/api/atm-decay/history` shows same-day monotonic rows through the current intraday window.
  - Blocking: none
- [x] P0: verify ActiveOptions runtime path remains live under the shared-input path.
  - Owner: Codex
  - Definition of Done: `active_options_input.valid=true`, fresh source timestamps persist, and live rows remain present in diagnostics/logs.
  - Blocking: none

## Parking Lot
- [ ] Continue the existing cross-session work item that validates `snapshot_version_iv_probe` on a fast-cadence websocket ATM IV source instead of the currently suppressed `rest` cadence.
- [ ] If operators need a one-command rerun, package this audit sequence into a dedicated diagnostics script rather than repeating ad hoc shell snippets.
- [ ] Investigate why ActiveOptions currently keeps fixed slots `1..5` but does not sustain five real contracts, with slot 5 fully placeholder during the sampled intraday window.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Confirmed intraday `L0 ingest/runtime`, `L1 compute freshness`, `L3 payload continuity`, `ATM live continuity`, and `ActiveOptions live continuity` all passed (2026-03-26 09:39 ET)
- [x] Captured the current diagnostic suppression reason `non_reactive_iv_source:rest` so IV freshness is not misclassified as a live runtime failure (2026-03-26 09:39 ET)
- [x] Added `scripts/diag/audit_intraday_core_flow.py` to rerun the core intraday audit in one command with text and JSON outputs (2026-03-26 09:44 ET)
- [x] Verified ActiveOptions header columns (`SYM/T/STRIKE/IMP/VOL/FLOW`) remained structurally valid across 30 live WS frames, while also proving the five-row contract is currently maintained via placeholders rather than five persistent real contracts (2026-03-26 09:50 ET)

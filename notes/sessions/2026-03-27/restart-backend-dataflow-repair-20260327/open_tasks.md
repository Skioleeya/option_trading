# Open Tasks

## Priority Queue
- [x] P0: restart the backend and determine why live dataflow stayed at `version=0/chain_size=0` after the prior reboot.
  - Owner: Codex
  - Definition of Done: the root cause is identified with direct evidence and the backend is restored to live chain updates.
  - Blocking: none
- [x] P1: verify whether the empty-chain state is a runtime defect or a launch-environment defect.
  - Owner: Codex
  - Definition of Done: sandbox vs non-sandbox connectivity probes are compared and the failing layer is identified.
  - Blocking: none
- [x] P1: restore a strict fresh-launch backend path with live Arrow IPC and live chain payloads.
  - Owner: Codex
  - Definition of Done: strict backend restart on the real host environment yields `rust_started=true`, `transport.status=OK`, and non-zero `chain_size/version`.
  - Blocking: none

## Parking Lot
- [x] The previously observed `/v2/socket/token` outage was a sandbox launch artifact in this session, not a persistent broker outage in the real host environment.
- [x] ActiveOptions still sampled as `DEGRADED` for some real rows because of missing gamma inputs; transport recovery itself is complete.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Proved the empty-chain backend was launched in a sandboxed network context and that this blocked both broker endpoint profiles. (2026-03-27 09:35 ET)
- [x] Re-ran the broker quote probe outside the sandbox and confirmed both endpoint profiles returned live SPY quotes. (2026-03-27 09:36 ET)
- [x] Replaced the sandboxed backend with an external strict backend instance and confirmed live Arrow IPC, live chain data, and `atm_status=LIVE`. (2026-03-27 09:37 ET)

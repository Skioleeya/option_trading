# Open Tasks

## Priority Queue
- [ ] P1: Retire versioned Wave 4-10 generated-extension candidate fallbacks. SUPERSEDED-BY: `2026-04-01/wave11-small-python-cleanup`
  - Owner: Codex
  - Definition of Done: the default `_native_generated/l0_rust.pyd` path is refreshable again and the runtime no longer needs wave-specific probing.
  - Blocking: external process still locks the default generated extension path.
- [ ] P1: Continue `shared/services/l0_runtime/services/*` migration with the next bounded owner cluster. SUPERSEDED-BY: `2026-04-01/wave11-small-python-cleanup`
  - Owner: Codex
  - Definition of Done: one additional services cluster moves to Rust-backed owner semantics without widening beyond L0.
  - Blocking: pick the next cluster after poller helper closure.
- [ ] P2: Split `shared/services/l0_runtime/services/orchestration/orchestrator.py` before any further owner migration there. SUPERSEDED-BY: `2026-04-01/wave11-small-python-cleanup`
  - Owner: Codex
  - Definition of Done: main-loop responsibilities are decomposed into submodules and the file is back under the 400-line ceiling.
  - Blocking: bounded split session not started yet.

## Parking Lot
- [ ] Decide whether the next cleaner bounded slice is `services/runtime/services.py` residual wiring or direct poller scheduling owner cutover. SUPERSEDED-BY: `2026-04-01/wave11-small-python-cleanup`
- [ ] Evaluate whether tier2/tier3 expiry-date selection should move to Rust after scheduling ownership is split from metadata shaping. SUPERSEDED-BY: `2026-04-01/wave11-small-python-cleanup`

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave 10 poller helper cluster completed (2026-04-01 16:54:03 -04:00)

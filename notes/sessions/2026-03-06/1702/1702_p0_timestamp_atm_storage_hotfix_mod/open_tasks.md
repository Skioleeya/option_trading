# Open Tasks

## Priority Queue
- [x] P0: T0-1 Harden L0-L4 timestamp contract (`L0 as_of_utc` single-source timestamp).
  - Owner: Codex
  - Definition of Done: `data_timestamp/timestamp` bound to L0 source UTC, drift uses L2-L0 delta, contract tests added.
  - Blocking: None
- [x] P0: T0-2 Reduce ATM decay storage write amplification.
  - Owner: Codex
  - Definition of Done: JSONL append-only cold mirror, no per-tick `lrange + full rewrite`, JSONL-first recovery with legacy JSON compatibility.
  - Blocking: None
- [x] P1: SOP sync for behavior-level runtime contract changes.
  - Owner: Codex
  - Definition of Done: Updated `docs/SOP` coverage for L0/L1/L3/L4/system overview.
  - Blocking: None
- [x] P2: Add repeatable high-load benchmark for storage write amplification.
  - Owner: Codex
  - Definition of Done: Added `scripts/test/benchmark_atm_decay_storage.py` and recorded baseline metrics.
  - Blocking: None

## Parking Lot
- [ ] P1: Add runtime observability probe for `snapshot_version` vs `spy_atm_iv` drift.
- [ ] P1: ATM chart incremental render optimization at 5k history.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] L0 source timestamp contract and L3 drift/data timestamp wiring completed (2026-03-06 17:14 ET)
- [x] ATM decay cold persistence switched to JSONL append-only with legacy recovery bridge (2026-03-06 17:14 ET)

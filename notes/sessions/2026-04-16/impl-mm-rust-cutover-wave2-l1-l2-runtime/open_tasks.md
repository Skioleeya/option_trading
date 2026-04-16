# Open Tasks

## Priority Queue
- [x] P0: Rust snapshot MM metrics owner + L1 metadata passthrough
  - Owner: Codex
  - Definition of Done: `mm_snapshot_metrics` export available and `extra_metadata.mm_flow_metrics` populated
  - Blocking: None
- [x] P0: L2 feature vector MM fields + fused_signal passthrough
  - Owner: Codex
  - Definition of Done: feature extractors output MM fields and `DecisionOutput.data.fused_signal.mm_flow` populated
  - Blocking: None
- [ ] P1: Wave3 L3 assembly/presenter specialized consumption
  - Owner: Codex
  - Definition of Done: L3/L4 consumer contract and view mapping for `fused_signal.mm_flow` finalized
  - Blocking: Wave2 strict gate and parent child-order

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] OpenSpec Wave2 child proposal/design/tasks/spec created (2026-04-16 17:40 ET)
- [x] Rust `shared_rust/services.pyd` rebuilt with `mm_snapshot_metrics` export (2026-04-16 17:43 ET)
- [x] Targeted MM tests passed (2026-04-16 17:45 ET)

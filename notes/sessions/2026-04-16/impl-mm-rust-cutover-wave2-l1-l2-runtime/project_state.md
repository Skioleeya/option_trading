# Project State

## Snapshot
- DateTime (ET): 2026-04-16 17:47:16 -04:00
- Branch: chore/sync-all-local-changes-20260313
- Last Commit: e91cff0
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED` (Wave3 pending)

## Current Focus
- Primary Goal: Wave2 L1/L2 runtime MM exposure contract integration with Rust owner aggregation.
- Scope In:
  - Rust `mm_snapshot_metrics` owner in `shared_rust_services`
  - L1 `extra_metadata.mm_flow_metrics` injection
  - L2 feature vector MM fields + `DecisionOutput.data.fused_signal.mm_flow` passthrough
  - Wave2 OpenSpec child + SOP sync + targeted tests
- Scope Out:
  - L3 presenter/UI visualization refactor (Wave3)
  - Full 50ms multi-leg matching engine

## What Changed (Latest Session)
- Files:
  - shared_rust_services/src/mm_flow.rs
  - shared_rust_services/src/mm_flow_snapshot.rs
  - shared_rust_services/src/lib.rs
  - app/loops/mm_flow_metadata.py
  - app/loops/compute_metadata.py
  - l2_decision/feature_store/extractors_common.py
  - l2_decision/feature_store/extractors_registry.py
  - l2_decision/feature_store/extractors_mm_flow.py
  - l2_decision/feature_store/extractors_vrp_impact.py
  - l2_decision/events/decision_events.py
  - app/loops/tests/test_mm_flow_metadata.py
  - app/loops/tests/test_compute_metadata_mm_flow.py
  - l2_decision/tests/test_decision_output_mm_flow.py
  - docs/SOP/L1_LOCAL_COMPUTATION.md
  - docs/SOP/L2_DECISION_ANALYSIS.md
  - openspec/changes/impl-20260416-mm-rust-cutover-wave2-l1-l2-rust-runtime/*
- Behavior:
  - Compute loop now emits `extra_metadata.mm_flow_metrics` from Rust snapshot aggregation.
  - L2 feature store now includes MM exposure/pressure/counter metrics.
  - `DecisionOutput.data.fused_signal` now carries `mm_flow` map for downstream L3 payload.
  - L2 extractor registry split into smaller modules to reduce coupling and file size.
- Verification:
  - Added/ran targeted pytest for MM metadata and output contract.
  - Rebuilt `shared_rust/services.pyd` with new `mm_snapshot_metrics` export.

## Risks / Constraints
- Risk 1: `complex_spread_count` in Wave2 is snapshot-level approximation, not millisecond trade-cluster matcher.
- Risk 2: L3 UI consumption of `fused_signal.mm_flow` not yet specialized (Wave3).

## Next Action
- Immediate Next Step: run strict session validation to green and close Wave2 task chain.
- Owner: Codex

# Project State

## Snapshot
- DateTime (ET): 2026-04-21 17:57:10 -04:00
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Replace the pure in-memory `pending_labels` owner with deterministic startup replay from persisted feature/label tiers so backend restarts no longer destroy 60-minute label continuity.
- Scope In:
  - `shared_rust_services/src/research_pending_labels.rs`
  - `shared_rust_services/src/research_store.rs`
  - `shared_rust_services/src/lib.rs`
  - `app/loops/tests/test_research_store_mm_flow_persistence.py`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - session/context sync files
- Scope Out:
  - no new fallback store or sidecar state file for `pending_labels`
  - no changes to EOD thresholds or classification rules
  - no unrelated fix for the pre-existing `ArrowIpcReader.close(): Already borrowed` shutdown bug surfaced during restart verification

## What Changed (Latest Session)
- Files:
  - `shared_rust_services/src/research_pending_labels.rs`
  - `shared_rust_services/src/research_store.rs`
  - `shared_rust_services/src/lib.rs`
  - `app/loops/tests/test_research_store_mm_flow_persistence.py`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- Behavior:
  - `ResearchFeatureStore` startup now replays the latest persisted feature day against the corresponding label tier.
  - Missing but already-matured labels are regenerated immediately on startup from persisted feature history.
  - Unmatured entries are restored into `pending_labels` from persisted feature history instead of starting from an empty in-memory queue.
  - The 20260421 recovered label file grew from `3265` rows to `14386` rows after the new startup replay ran on real host.
  - Rerunning 20260421 archive/classification after label recovery now yields `primary_day_type=balance_day`, `context_modifiers=[vol_crush]`, `quality=PASS`.
- Verification:
  - `cargo build --release --manifest-path shared_rust_services/Cargo.toml --target-dir tmp/cargo_target_runtime` passed.
  - `run-pytest app/loops/tests/test_research_store_mm_flow_persistence.py` passed (`6 passed`).
  - Real-host startup replay raised `label_20260421` row count to `14386` and EOD rerun published synchronized PASS manifests.

## Risks / Constraints
- Risk 1: Full-stack restart verification is currently blocked by a pre-existing shutdown bug (`ArrowIpcReader.close(): Already borrowed`) outside this session’s pending-label owner change.
- Risk 2: Startup replay restores continuity from persisted feature history only; if feature history itself is missing, label recovery still must fail fast.

## Next Action
- Immediate Next Step: Decide whether to open a separate session for the unrelated `ArrowIpcReader.close()` shutdown bug discovered during real-host restart verification.
- Owner: Codex

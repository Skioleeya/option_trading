# Project State

## Snapshot
- DateTime (ET): 2026-04-21 17:37:30 -04:00
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Hard-cut the research persistence and EOD archive owners so backend restarts cannot corrupt `research_raw`, then close the remaining 20260421 archive blockage by proving the `research_label` shortfall root cause.
- Scope In:
  - `l0_ingest/l0_rust/src/research_store_storage.rs`
  - `shared_rust_services/src/research_store.rs`
  - `l3_assembly/reactor.py`
  - `app/loops/shared_state.py`
  - `app/loops/compute_loop.py`
  - `app/loops/broadcast_loop.py`
  - `app/loops/housekeeping_loop.py`
  - `app/routes/health.py`
  - `infra/ops_cli/start_backend.py`
  - `infra/ops_cli/start_all.py`
  - `scripts/diagnostics/eod_bucket_archive.py`
  - `scripts/diagnostics/eod_bucket_publish.py`
  - targeted runtime / archive / restart tests
  - 20260421 raw recovery and archive rerun evidence
  - 20260421 label shortfall forensic evidence
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `最新的启动步骤文档.md`
- Scope Out:
  - No compatibility path for partial EOD publish or non-fatal research append failures
  - No fallback research root or degraded restart behavior
  - No silent downgrade of `LOW_QUALITY_DAY` once the archive runner legitimately emits it

## What Changed (Latest Session)
- Files:
  - `l0_ingest/l0_rust/src/research_store_storage.rs`
  - `shared_rust_services/src/research_store.rs`
  - `l3_assembly/reactor.py`
  - `app/loops/shared_state.py`
  - `app/loops/compute_loop.py`
  - `app/loops/broadcast_loop.py`
  - `app/loops/housekeeping_loop.py`
  - `app/routes/health.py`
  - `infra/ops_cli/start_backend.py`
  - `infra/ops_cli/start_all.py`
  - `scripts/diagnostics/eod_bucket_archive.py`
  - `scripts/diagnostics/eod_bucket_publish.py`
  - `app/tests/test_start_backend_strict_restart.py`
  - `app/tests/test_health_route_diagnostics.py`
  - `app/loops/tests/test_compute_loop_gpu_dedup.py`
  - `app/loops/tests/test_research_store_mm_flow_persistence.py`
  - `scripts/test/test_eod_bucket_archive.py`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `最新的启动步骤文档.md`
- Behavior:
  - Research parquet writes no longer overwrite the target path in place; they stage to a same-directory temp file, `fsync`, atomically rename, then `fsync` the parent directory.
  - `ResearchFeatureStore` no longer falls back to a temp root when the configured root is invalid; startup now fails immediately on an unusable explicit root.
  - Research append failure is no longer logged as non-fatal. It marks runtime fatal, trips `/health` to `503`, and stops loop progression.
  - Backend restart is no longer `pkill`-then-replace. `start-backend` / `start-all` now attempt graceful termination and fail nonzero if the old backend does not exit in time.
  - EOD archive no longer exposes partial visible output while still validating sources. It stages daily/regime/report outputs first and only publishes final paths after all required source validation and manifest/report generation succeed.
  - 20260421 `research_raw` was deterministically rebuilt from the intact same-day feature parquet by projecting the exact raw schema fields; the original 4-byte corrupt file was preserved as a `.bak` evidence artifact.
  - 20260421 archive/classification was rerun successfully on the repaired raw file and published clean final outputs under `data/cold`.
  - The remaining `research_label` shortfall is now proven to come from repeated backend restarts resetting the in-memory `pending_labels` queue before entries could survive the 60-minute horizon. `label_20260421.parquet` stops at `stored_at≈12:24:46 ET`, exactly matching the next `[BOOT] 12:24:44 ET`, and the rest of the day contains many more boots less than 60 minutes apart.
- Verification:
  - Targeted Python tests passed for health diagnostics, restart semantics, compute fatal path, research store root strictness, and staged archive publish behavior.
  - Rust tests and release builds passed for the modified runtime crates.
  - Runtime artifacts were rebuilt for `shared_rust/services.so` and `shared/services/l0_runtime/_native_generated/l0_rust.so`.
  - Real-host startup, health, persistence diagnostics, raw rebuild, archive rerun, and manifest sync all succeeded.
  - Forensic label evidence now ties the `3265` label rows to the single uptime window between the `10:27 ET` and `12:24 ET` backend boots.

## Risks / Constraints
- Risk 1: The corruption path is fixed and 20260421 raw has been recovered, but the 20260421 archive remains `LOW_QUALITY_DAY / INCOMPLETE_SOURCE` because repeated historical restarts had already destroyed label continuity for that day.
- Risk 2: Archive publish now fails if a final target day already exists; reruns require explicit quarantine/cleanup of stale final outputs rather than overwrite semantics.

## Next Action
- Immediate Next Step: Decide whether the proven historical restart-driven label loss should be accepted as the terminal state for 20260421 or whether labels need an owner-level recovery path in a new session.
- Owner: Codex

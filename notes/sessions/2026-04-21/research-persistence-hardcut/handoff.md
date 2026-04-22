# Handoff

## Session Summary
- DateTime (ET): 2026-04-21 17:37:30 -0400
- Goal: hard-cut the research persistence, backend restart, and EOD archive owners so the proven `research_raw` corruption path is removed and corrupt required inputs fail fast instead of degrading.
- Outcome: completed. Future writes now commit atomically, research persistence failure is fatal, backend restart is graceful-or-fail, EOD archive publishes staged outputs only after full validation, `python3 manage.py validate-session --strict` passed, and real-host `start-all` plus health/diagnostic verification succeeded. On top of the code fix, 20260421 `research_raw` was rebuilt from the intact same-day feature parquet, the stale pre-hardcut cold-output directory was quarantined, and the archive rerun published clean final outputs. The day still classifies as `LOW_QUALITY_DAY / INCOMPLETE_SOURCE`, and the remaining reason is now closed: repeated backend restarts during the session kept wiping the in-memory `pending_labels` queue before entries could survive the 60-minute label horizon.

## What Changed
- Code / Docs Files:
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
- Runtime / Infra Changes:
  - research parquet append uses temp-file + `fsync` + atomic rename + parent-dir `fsync` rather than same-path overwrite.
  - invalid configured research root now fails construction immediately; no temp-root fallback remains.
  - research append failure now trips runtime fatal state, surfaces in `/health` and `/debug/persistence_status`, and stops loop progression.
  - backend startup now refuses to replace a still-running backend after a bounded graceful-stop timeout.
  - EOD archive now stages daily/regime/report artifacts and only publishes them after all source integrity checks and report generation succeed.
- Commands Run:
  - `python3 -m py_compile app/loops/compute_loop.py app/loops/shared_state.py app/routes/health.py infra/ops_cli/start_backend.py infra/ops_cli/start_all.py scripts/diagnostics/eod_bucket_archive.py scripts/diagnostics/eod_bucket_publish.py l3_assembly/reactor.py`
  - `.venv/bin/python manage.py run-pytest app/tests/test_health_route_diagnostics.py app/loops/tests/test_research_store_mm_flow_persistence.py scripts/test/test_eod_bucket_archive.py`
  - `.venv/bin/python manage.py run-pytest app/tests/test_start_backend_strict_restart.py app/loops/tests/test_compute_loop_gpu_dedup.py app/tests/test_health_route_diagnostics.py app/loops/tests/test_research_store_mm_flow_persistence.py scripts/test/test_eod_bucket_archive.py`
  - `cargo test --manifest-path l0_ingest/l0_rust/Cargo.toml`
  - `cargo build --release --manifest-path shared_rust_services/Cargo.toml --target-dir tmp/cargo_target_runtime`
  - `cargo build --release --manifest-path l0_ingest/l0_rust/Cargo.toml --target-dir tmp/cargo_target_runtime_l0`
  - `python3 manage.py validate-session --strict`
  - `python3 manage.py start-all`
  - `python3 manage.py start-all --verify-only`
  - `curl -sS -D - http://127.0.0.1:8001/health`
  - `curl -sS http://127.0.0.1:8001/debug/persistence_status`
  - `ss -ltnp '( sport = :8001 or sport = :5173 or sport = :6380 )'`
  - `.venv/bin/python <rebuild 20260421 raw parquet from feature projection>`
  - `.venv/bin/python manage.py run-eod-bucket --date 20260421 --python-exe .venv/bin/python --repo-root /home/lenovo/projects/Option_v3 --config-path scripts/diagnostics/config/eod_bucket_thresholds.json --data-root data --out-root data/cold --run-label manual-rebuild`
  - forensic inspection of `label_20260421.parquet`, historical feature/label ratios, and `logs/backend_runtime.current.log` boot timeline

## Verification
- Passed:
  - Python syntax compilation for the modified runtime/infra/archive modules.
  - `run-pytest` targeted suites: health diagnostics, restart semantics, compute fatal path, research store root strictness, and staged archive publish behavior (`28 passed`).
  - `cargo test --manifest-path l0_ingest/l0_rust/Cargo.toml` (`4 passed`).
  - Rust release builds for `shared_rust_services` and `l0_ingest/l0_rust`.
  - `python3 manage.py validate-session --strict`.
  - real-host `python3 manage.py start-all` followed by `start-all --verify-only`: `Redis 6380 True`, `Backend 8001 True`, `Frontend 5173 True`.
  - real-host `curl http://127.0.0.1:8001/health`: `HTTP/1.1 200 OK` with `{"status":"ok","fatal_runtime_error":null,"research_persistence":{"healthy":true,"fatal_error":null}}`.
  - real-host `curl /debug/persistence_status`: runtime health remained clean, `research_store.write_failures=0`, `research_persistence.healthy=true`, and transport/gateway diagnostics were present.
  - real-host `ss -ltnp`: listeners confirmed on `127.0.0.1:6380`, `0.0.0.0:8001`, and `0.0.0.0:5173`.
  - rebuilt `data/research/raw/raw_20260421.parquet` is readable parquet with `16455` rows and the exact raw schema columns.
  - `manage.py run-eod-bucket --date 20260421 ...` republished `data/cold/daily/20260421/manifest.json`, `data/cold/reports/20260421_quality.json`, and `data/cold/by_regime/INCOMPLETE_SOURCE/20260421/manifest.json`; `check_eod_manifest_sync` reported `ok=true`.
  - forensic label evidence: `label_20260421.parquet` mtime is `2026-04-21 12:24:46 ET`, its `stored_at` range is `11:27 ET -> 12:24 ET`, and the next log event is `[BOOT] 12:24:44 ET`; subsequent boots at `12:38, 12:53, 13:46, 14:13, 14:34, 14:50, 15:02, 15:15, 15:37, 15:39 ET` were all less than 60 minutes apart, so no later pending-label cohort could mature.
- Failed / Not Run:
  - 20260421 still blocks at quality gate because the historical restarts already destroyed label continuity for that day; this is now a proved terminal data-quality condition unless a separate label-recovery owner is introduced.

## Pending
- Must Do Next:
  - decide whether 20260421 should remain permanently `LOW_QUALITY_DAY / INCOMPLETE_SOURCE` with the documented evidence, or whether label recovery belongs in a separate explicit session.
- Nice to Have:
  - add one deeper interruption-boundary regression around atomic parquet replacement.

SOP-EXEMPT: none; runtime behavior changed and SOP docs were updated.
OPENSPEC-EXEMPT: hard-cut runtime integrity repair on existing persistence/startup/archive contracts; no new product/runtime capability or schema surface introduced.

## Debt Record (Mandatory)
- DEBT-EXEMPT: one historical data-quality item remains because repeated same-day restarts already destroyed 20260421 label continuity before the hard-cut landed.
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-21
- DEBT-RISK: medium; current runtime is fixed and verified, but 20260421 remains blocked unless the team explicitly accepts the day as low quality or adds a separate label-recovery mechanism.
- DEBT-NEW: 0
- DEBT-CLOSED: 1
- DEBT-DELTA: -1
- DEBT-JUSTIFICATION: closed the proven root-cause debt around non-atomic research persistence plus blind backend restart semantics, recovered raw/archive outputs, and reduced the remaining issue to a historical label-loss fact pattern.
- RUNTIME-ARTIFACT-EXEMPT: rebuilt `shared_rust/services.so` and `shared/services/l0_runtime/_native_generated/l0_rust.so` from local release builds in this session.

## How To Continue
- Start Command: `python3 manage.py start-all`
- Key Logs: `logs/backend_runtime.current.log`, `/debug/persistence_status`, `data/cold/reports/20260421_quality.json`
- First File To Read: `notes/sessions/2026-04-21/research-persistence-hardcut/project_state.md`

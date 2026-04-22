# Handoff

## Session Summary
- DateTime (ET): 2026-04-21 17:57:10 -0400
- Goal: Replace the pure in-memory `pending_labels` owner so backend restarts no longer wipe the 60-minute label maturation window.
- Outcome: completed. `ResearchFeatureStore` now rebuilds pending label continuity by replaying the latest persisted feature day against the corresponding label tier on startup, recovers any missing matured labels immediately, and restores the remaining live pending queue from persisted feature history. On real host, this raised `label_20260421` from `3265` rows to `14386` rows and allowed the 20260421 archive rerun to publish `quality=PASS` with `primary_day_type=balance_day` and `vol_crush` context.

## What Changed
- Code / Docs Files:
  - `shared_rust_services/src/research_pending_labels.rs`
  - `shared_rust_services/src/research_store.rs`
  - `shared_rust_services/src/lib.rs`
  - `app/loops/tests/test_research_store_mm_flow_persistence.py`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- Runtime / Infra Changes:
  - Startup no longer trusts an empty in-memory `pending_labels` queue. It replays the latest persisted feature day, rehydrates unmatured pending entries, and regenerates missing matured labels before normal runtime continues.
  - No new fallback state file was introduced; feature/label persisted tiers remain the single owner for recovery.
- Commands Run:
  - `cargo build --release --manifest-path shared_rust_services/Cargo.toml --target-dir tmp/cargo_target_runtime`
  - `cp tmp/cargo_target_runtime/release/libservices.so shared_rust/services.so`
  - `.venv/bin/python manage.py run-pytest app/loops/tests/test_research_store_mm_flow_persistence.py`
  - `python3 manage.py start-all` (real-host attempt to load the new owner; surfaced an unrelated shutdown bug while still executing startup replay)
  - `.venv/bin/python manage.py run-eod-bucket --date 20260421 --python-exe .venv/bin/python --repo-root /home/lenovo/projects/Option_v3 --config-path scripts/diagnostics/config/eod_bucket_thresholds.json --data-root data --out-root data/cold --run-label label-recovery`
  - `python3 manage.py validate-session --strict`

## Verification
- Passed:
  - `cargo build --release --manifest-path shared_rust_services/Cargo.toml --target-dir tmp/cargo_target_runtime`
  - `.venv/bin/python manage.py run-pytest app/loops/tests/test_research_store_mm_flow_persistence.py` (`6 passed`)
  - real-host label recovery evidence: `data/research/label/label_20260421.parquet` increased from `3265` rows to `14386` rows; latest `stored_at` moved to `2026-04-21T21:54:50.188478485+00:00`
  - real-host archive rerun after label recovery: `primary_day_type=balance_day`, `modifiers=vol_crush`, `quality=PASS`, `check_eod_manifest_sync ok=true`
  - `python3 manage.py validate-session --strict`
- Failed / Not Run:
  - `python3 manage.py start-all --verify-only` stayed red for backend because the restart attempt exposed a pre-existing shutdown-path bug in `ArrowIpcReader.close(): Already borrowed`; this session did not change that owner.

## Pending
- Must Do Next:
  - decide whether the unrelated `ArrowIpcReader.close()` shutdown bug needs its own follow-up session.
- Nice to Have:
  - add explicit diagnostics for startup-recovered label rows if operations wants this visible in `/debug/persistence_status`.

SOP-EXEMPT: none; runtime behavior changed and SOP docs were updated.
OPENSPEC-EXEMPT: owner-level runtime continuity fix on existing research persistence contracts; no new product/API/schema surface introduced.

## Debt Record (Mandatory)
- DEBT-EXEMPT: no new debt in the pending-label owner itself; the only unresolved issue observed here is a pre-existing shutdown-path bug outside this session’s scope.
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-23
- DEBT-RISK: low for this session’s objective; pending-label continuity is fixed, but real-host graceful restart evidence remains partially blocked until the existing IPC shutdown bug is handled.
- DEBT-NEW: 0
- DEBT-CLOSED: 1
- DEBT-DELTA: -1
- DEBT-JUSTIFICATION: closed the label-continuity root cause and removed the restart-driven label-loss condition from 20260421.
- RUNTIME-ARTIFACT-EXEMPT: rebuilt `shared_rust/services.so` from local release build in this session.

## How To Continue
- Start Command: `python3 manage.py start-all`
- Key Logs: `logs/backend_runtime.current.log`, `data/research/label/label_20260421.parquet`, `data/cold/reports/20260421_quality.json`
- First File To Read: `notes/sessions/2026-04-21/research-label-pending-hardcut/project_state.md`

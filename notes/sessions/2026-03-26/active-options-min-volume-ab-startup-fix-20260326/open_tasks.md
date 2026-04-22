# Open Tasks

## Priority Queue
- [x] P0: fix the degraded-startup `spot=None` crash that blocked the ActiveOptions min-volume A/B restart.
  - Owner: Codex
  - Definition of Done: `lifespan` coerces a missing initial spot to `0.0`, a focused regression test covers it, and startup docs capture the requirement.
  - Blocking: none
- [x] P1: restore one healthy backend restart path so bounded ActiveOptions A/B can be re-run after process replacement.
  - Owner: Codex
  - Definition of Done: one restarted backend instance reaches healthy `:8001` service with non-empty chain data, Arrow IPC attached, and quote connectivity restored.
  - Completion Evidence: elevated strict restart reached healthy `:8001`, `transport.status=OK`, `gateway.connected=true`, `chain_size=102`, and `logs/backend_runtime.elevated_strict.log` recorded `Startup connectivity probe passed: symbol=SPY.US rows=1`.
- [x] P1: re-run the bounded `FLOW_ACTIVE_MIN_VOLUME` live A/B.
  - Owner: Codex
  - Definition of Done: one controlled threshold comparison is captured under healthy runtime conditions and shows whether sparse winners are policy-driven or source-coverage driven.
  - Completion Evidence: baseline strict `100` showed `rows_real_non_synthetic=5`, `rows_synthetic_fallback=0`, `filtered_candidates_count=51`; strict `10` later showed `rows_real_non_synthetic=5`, `rows_synthetic_fallback=0`, `live_rows=5`, `min_volume_threshold=10`, with min10 candidate counts observed between `45` and `88` as the market moved.
- [ ] P1: capture one same-version raw-chain vs displayed-top5 sparse-window artifact from the server-side runtime path.
  - Owner: Codex
  - Definition of Done: one live sample preserves the same source version for raw chain and displayed Top5, then explains whether the sparse-output case is policy-driven or source-coverage driven.
  - Progress: `/debug/active_options_capture` and `scripts/diag/capture_same_version_active_options.py` now produce version-aligned artifacts; `tmp/active_options_same_version_capture.json` captured `input_source_version=306`, `payload_source_version=306`, `chain_size=100`, `filtered_candidates_count=86`.
  - Blocking: requires a naturally sparse live window; a 180-second watch only reached `46` filtered candidates against `5` displayed real rows, so `tmp/active_options_same_version_sparse_capture.json` is aligned but not sparse.

## Parking Lot
- [ ] Check whether `scripts/ops/start_backend.ps1` should have an explicit strict-hotfix mode instead of coupling `-HotfixActiveOptions` to degraded startup.
- [ ] Investigate why the non-elevated restart path was flaky earlier while the elevated strict restart succeeded.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added a debug-only same-version ActiveOptions capture endpoint and script, then verified it with focused diagnostics tests and compileall (2026-03-26 14:31 ET)
- [x] Restored `:8001` again via elevated strict/min10 restart after the failed non-elevated restart, then captured aligned server-side artifacts at `tmp/active_options_same_version_capture.json` and `tmp/active_options_same_version_sparse_capture.json` (2026-03-26 14:44 ET)
- [x] Recovered a healthy backend instance via elevated strict restart and verified Arrow IPC + quote connectivity were back (`transport.status=OK`, `gateway.connected=true`, `chain_size=102`) (2026-03-26 14:10 ET)
- [x] Completed the bounded live `FLOW_ACTIVE_MIN_VOLUME` A/B under healthy runtime conditions; lowering to `10` expanded the candidate pool in sampled windows but did not change the fully-real Top5 outcome in those windows (2026-03-26 14:18 ET)
- [x] Captured directional raw-chain artifacts at `tmp/active_options_artifact_min10.json` and `tmp/active_options_artifact_min10_warm.json`, then confirmed the warmed capture is not source-version aligned with the server payload (2026-03-26 14:18 ET)
- [x] Reproduced the blocked A/B restart on a real runtime path and traced it to `app/lifespan.py` comparing `None > 0` during startup bootstrap (2026-03-26 13:56 ET)
- [x] Added `app/tests/test_lifespan_startup.py` to prove `spot=None` is normalized to `0.0` and no `TypeError` is raised in the startup context (2026-03-26 13:58 ET)
- [x] Updated `docs/SOP/SYSTEM_OVERVIEW.md` to require non-negative spot normalization before the startup near-ATM repair gate (2026-03-26 13:58 ET)

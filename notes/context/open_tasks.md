# Open Tasks (Index)

## Active Session Tasks
- Path: notes/sessions/2026-07-09/branch-convergence-master-main/open_tasks.md

## Current Priority
- PR `#5` is open from `codex/research-persistence-startup-fixes-20260423` to `master`.
- GitHub default branch is now `master`, and `origin/main` has been force-aligned to the same commit as `origin/master`.

## Global Backlog (Cross-Session)
- [x] Preserve valid L0 source spot through the L1 empty-snapshot startup path so first-tick research persistence no longer fatals on `snapshot.spot must be finite and > 0`. (2026-04-23 09:53 ET)
- [x] Hard-cut runtime research persistence to a single canonical parquet owner, remove silent input fallback, and switch EOD archive runtime input to canonical. (2026-04-23 09:21 ET)
- [ ] Monitor repo growth and push latency now that `data/cold` is versioned by explicit user request.
- [x] Fully resync `最新的启动步骤文档.md` so its meaning exactly matches the current Windows startup implementation and host verification boundary. (2026-04-22 18:40 ET)
- [x] Refresh `最新的启动步骤文档.md` from real-host Windows startup evidence and remove the frontend runtime/startup blockers in the standard `start-all` path. (2026-04-22 18:33 ET)
- [x] Open and merge a PR from `chore/master-sync-clean-20260422` into `master` because direct `origin/master` pushes are blocked by repository rules. (2026-04-22 18:10 ET)
- [x] Link local `Option_v4` origin to the provided GitHub SSH remote URL. (2026-04-22 17:09 ET)
- [x] Restore local Git provenance in `Option_v4` so branch/head/origin are no longer `unknown`. (2026-04-22 16:58 ET)
- [x] Remove sandbox-local frontend `spawn EPERM` by hard-cutting the strict dev launcher to the Vite JS API path. (2026-04-22 17:09 ET)
- [ ] Decide whether to restart the original WSL stack after the completed `Option_v4` mirror copy.
- [ ] If the user later wants Windows-native development, scope it as a separate rebuild/migration session rather than extending Scheme A.
- [x] Fix host TLS credential chain (`SEC_E_NO_CREDENTIALS`) so workspace-local `python manage.py build-pyd --check --all` can fetch crates.io and complete. (2026-04-22 16:31 ET)
- [x] Replace the copied `Option_v3` native `.pyd` owners in `Option_v4` with locally rebuilt artifacts from this repo and install them to the runtime owner paths. (2026-04-22 16:43 ET)
- [ ] Decide whether the host `vm.overcommit_memory` warning needs an explicit repo-side diagnostic or SOP addendum.
- [x] Reload the corrected Windows 10 WSL NAT + localhostForwarding config and re-verify Windows `localhost:5173` and `localhost:8001`.
- [x] If localhost still fails after the NAT config reload, identify the remaining host owner with fresh evidence.
- [ ] Execute postmarket 120-second live runtime verification (Redis/backend/frontend + mm_flow key metrics non-zero evidence).
- [ ] Decide whether more non-push gateway internals need to be promoted into the borrow-free diagnostics handle.
- [ ] Add one targeted runtime regression that proves the final parquet path never becomes a truncated visible target during an interrupted atomic commit.
- [ ] Capture real-host full-stack evidence for the new graceful-or-fail backend restart path and fatal research persistence health contract.
- [ ] Add dedicated model test for duplicate/out-of-range `slot_index` sanitation in ActiveOptions.
- [ ] Monitor strict startup gate telemetry for `writer_not_ready_timeout` in live market open window; retune timeout only with evidence now that the bootstrap-safe stale gate is live.
- [ ] Capture one full market-session Sub-wave F dual-run compare and append no-divergence evidence in handoff.
- [ ] Verify/close residual `tmp/pytest_cache` write-warning path (`nodeids`) for non-escalated test runs.
- [ ] Continue `shared/services` retirement with `l0_runtime` (Sub-wave D storage/utility assessment completed; tactical-triad wrapper retirement closed in Wave B; next: namespace convergence and remaining neutral-surface retirements).
- [ ] Collapse temporary Rust-only service module names into the final `shared_rust.services` namespace.
- [ ] Continue governance debt wave after `dashboardStore` split: `AtmDecayChart.tsx` and `ui_state_tracker.py` line-length remediation.
- [ ] Capture 60s real-host WS continuity evidence for `version/source_timestamp/spot` progression after Arrow IPC transport fix.
- [ ] In a higher-volatility real market window, resample `SPY.US` distinct midpoint cadence to confirm whether the current business-side “real-time feel” is sufficient now that transport loss is removed.
- [ ] Capture one live flat-price window and verify the new quote-lane telemetry-only payload path keeps L4 cadence diagnostics fresh without unnecessary spot/version churn.
- [ ] Investigate the residual postmarket warnings from `shared/services/active_options_runtime.py` and `DepthProfile EMA`; they did not block startup or proxy verification in this session.
- [x] Hard-cut Redis persistence ownership to WSL ext4 and eliminate the `/mnt/e` + oversized AOF startup bottleneck.
- [x] Produce and verify a source-only `Option_v4` copy checklist that preserves current source and excludes runtime artifacts.
- [x] Execute the real Scheme A source-only mirror into `E:\US.market\Option_v4`.
- [x] Close the Windows browser `localhost:5173` failure by correcting the WSL localhost-forwarding owner state.
- [x] Clear the unrelated frontend type-test debt so `npm --prefix l4_ui run build` is green again.
- [x] Quantify whether live SPY distinct-value cadence < `1Hz` was caused by midpoint-owner acceptance after the live-spot fast-lane cutover; the transport root cause is now closed by the queued Arrow IPC rewrite.
- [x] Continue tracing why most raw `SPY.US` depth pushes do not survive into Python `update_spot_from_source()`; final root cause was Arrow IPC single-slot overwrite, now replaced by ordered queued transport with zero drop/gap evidence on real host.
- [x] Remove the proven research persistence corruption path caused by forced backend restart during non-atomic same-path parquet rewrite.
- [x] Recover 20260421 `research_raw` and republish the 20260421 archive outputs on the fixed contract.
- [x] Prove the remaining 20260421 label shortfall is caused by repeated restart-driven loss of the in-memory `pending_labels` queue.
- [x] Replace pure in-memory `pending_labels` ownership with startup replay from persisted feature/label tiers and recover the 20260421 archive classification to `quality=PASS`.
- [x] Remove the `ArrowIpcReader.close(): Already borrowed` shutdown-path restart blocker on the real host.
- [x] Remove the remaining `RustQuoteRuntime` REST-path `Already borrowed` warnings caused by concurrent native gateway access.
- [x] Move `RustQuoteRuntime.diagnostics()` off the live gateway and onto a borrow-free diagnostics owner surface.
- [x] Close the three frontend review regressions in `vite.config.ts`, `dashboardStore.ts`, and `AtmDecayChart.tsx` with targeted build/store/chart verification.

## Process
- Task details and completion evidence belong in the session-local open_tasks.md.
- Keep this file as the long-horizon queue and session pointer only.

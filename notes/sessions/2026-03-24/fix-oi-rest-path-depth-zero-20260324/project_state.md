# Project State

## Snapshot
- DateTime (ET): 2026-03-24 11:57:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `21b928c07b79f41f3212449e2de2e57271d673aa`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Stabilize live ATM anchor persistence by preventing non-positive WS prices from erasing recovered anchor-leg quotes, suppressing flat opening `0/0/0` ticks, discarding persisted flat-zero bad anchors during restore, allowing same-day intraday bootstrap lock on startup, and seeding the first post-lock repair/recompute path during startup.
- Scope In: `app/lifespan.py`, `l0_ingest/feeds/chain_state_store.py`, `l1_compute/analysis/atm_decay/runtime.py`, `l1_compute/analysis/atm_decay/storage.py`, `l1_compute/analysis/atm_decay/tracker.py`, focused L0/L1 tests, session notes, and SOP alignment.
- Scope Out: Broad refactors outside the L0/L1 runtime path.

## What Changed (Latest Session)
- Files:
  - `app/lifespan.py`
  - `l0_ingest/feeds/chain_state_store.py`
  - `l0_ingest/feeds/feed_orchestrator.py`
  - `l0_ingest/feeds/iv_baseline_sync.py`
  - `l0_ingest/feeds/option_chain_builder.py`
  - `l0_ingest/feeds/price_repair.py`
  - `l0_ingest/tests/test_chain_state_store.py`
  - `l0_ingest/tests/test_feed_orchestrator_startup_stagger.py`
  - `l0_ingest/tests/test_iv_baseline_sync.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `l1_compute/analysis/atm_decay/anchor.py`
  - `l1_compute/analysis/atm_decay/runtime.py`
  - `l1_compute/analysis/atm_decay/storage.py`
  - `l1_compute/analysis/atm_decay/tracker.py`
  - `l1_compute/tests/test_atm_decay_modular.py`
  - `l1_compute/tests/test_atm_decay_tracker.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Behavior:
  - `ChainStateStore` now allows REST price fallback for `bid/ask/last_price` only when a symbol has not yet received any positive WS price field, preserving WS ownership once valid live prices arrive.
  - `IVBaselineSync` still repairs anchor-leg prices after `calc_indexes()` batches, but that repair now flows through a shared bounded helper rather than bespoke inline logic.
  - `FeedOrchestrator` now performs a bounded `option_quote()` repair pass for `mandatory_symbols` on its startup/steady ticks, so anchor-leg price repair no longer waits for the 60-second IV sync loop.
  - `lifespan` now pushes restored ATM anchor legs into `mandatory_symbols` immediately after tracker initialization, closing the startup race where warm-up/repair could begin before housekeeping had synced anchor symbols.
  - Frontend `dashboardStore` no longer collapses ATM history when a new tick has the same `call/put/straddle` values but a newer timestamp; TradingView can now keep extending the line in time for flat periods.
  - ATM decay now emits a targeted diagnostic payload when raw percentage computation cannot proceed, including the locked call/put symbols and exact `bid/ask/last_price/mid_price` inputs.
  - Diagnostics are persisted separately from the main series in a dedicated cold JSONL file and Redis list key.
  - Tracker orchestration remains thin; anchor logic stays pure and storage remains isolated from the compute path.
  - Focused tests now cover exact leg-field capture and diagnostic persistence behavior.
  - Isolated verification confirmed `option_quote(SPY260324C652000.US)` can backfill `last_price` into `ChainStateStore`.
  - The runtime design no longer depends on `calc_indexes()` carrying price fields for startup ATM recovery; bounded `option_quote()` repair is now available both in IV batches and in orchestrator tick flow.
  - `ChainStateStore` no longer lets WS quote events with non-positive `bid/ask/last_price` overwrite an already recovered positive price, which prevents anchor-leg repairs from being immediately erased by empty live ticks.
  - ATM decay now suppresses the first post-lock decay sample when it is still a flat `0/0/0` opening tick, so the main ATM history waits for the first real post-lock move instead of persisting a misleading zero point.
  - ATM decay restore/deferred-restore now discards a persisted anchor when the latest ATM history row for that anchor is the same `locked_at` plus a flat `call/put/straddle = 0/0/0` opening point.
  - Storage now exposes a targeted `get_latest_history_point()` helper so bad-anchor screening does not need to replay the full ATM series.
  - Runtime cleanup removed the live `10:56:47 ET` bad anchor from Redis plus cold files; after restart the backend no longer restores that stale `0/0/0` ATM platform and instead serves `atm=null` until a new clean lock occurs.
  - `lifespan` now attempts one intraday bootstrap lock immediately from the startup `fetch_chain()` snapshot whenever the system is already in regular session and no valid anchor was restored, so same-day startup does not wait for a later warm-up path or the next trade date.
  - `AtmDecayTracker` now exposes `bootstrap_intraday_anchor()` for this startup-only path; it bypasses the post-start warm-up countdown but keeps existing session-time and valid-spot guards.
  - Startup bootstrap no longer reads the filtered `fetch_chain()['chain']` payload; `OptionChainBuilder` now exposes an unfiltered startup snapshot context so bootstrap can see the raw L0 store before `target_symbols` is populated.
  - `lifespan` now keeps a bounded startup retry window for intraday bootstrap, polling the current L0 spot + chain for up to 10 seconds so startup can lock the same-day anchor as soon as the first usable live snapshot arrives.
  - `FeedOrchestrator` now exposes a bounded one-shot `repair_symbols_once()` path for startup/runtime orchestration when app wiring already knows the exact anchor legs that need repair.
  - `OptionChainBuilder` now exposes that one-shot repair as a public orchestration API instead of forcing app startup to wait for the background management loop.
  - `AtmDecayTracker` now exposes `compute_current_decay()` so app startup can re-run decay immediately after a successful startup repair without reaching into private members.
  - `lifespan` now performs `bootstrap lock -> set mandatory symbols -> bounded one-shot repair -> immediate decay recompute` before background loops start, closing the startup gap where same-day lock succeeded but the first valid ATM point still had to wait for later orchestrator ticks.
  - `OptionChainBuilder` now exposes `refresh_subscriptions_once()` and `lifespan` uses it immediately after startup anchor capture so `mandatory_symbols` are pushed into `target_symbols` right away instead of waiting for the next orchestrator refresh cadence.
  - Startup recompute is no longer gated on `repaired > 0`; `lifespan` now attempts the first ATM decay recompute even when the bounded repair path finds no additional symbols to patch.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_feed_orchestrator_startup_stagger.py l1_compute/tests/test_atm_decay_tracker.py` -> 20 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_feed_orchestrator_startup_stagger.py l1_compute/tests/test_atm_decay_tracker.py` -> 19 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_iv_baseline_sync.py l0_ingest/tests/test_feed_orchestrator_startup_stagger.py l0_ingest/tests/test_chain_state_store.py l0_ingest/tests/test_builder_orchestration_support.py l1_compute/tests/test_atm_decay_tracker.py` -> 36 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_tracker.py` -> 11 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_chain_state_store.py` -> 15 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_tracker.py l1_compute/tests/test_atm_decay_modular.py` -> 22 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_modular.py l1_compute/tests/test_atm_decay_tracker.py` -> 25 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_tracker.py l1_compute/tests/test_atm_decay_modular.py` -> 26 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_fetch_chain_components.py l1_compute/tests/test_atm_decay_tracker.py l1_compute/tests/test_atm_decay_modular.py` -> 33 passed
  - `npm --prefix l4_ui run test -- dashboardStore` -> blocked by local `esbuild spawn EPERM`
  - Restarted backend after deleting `app:opening_atm:20260324`, `app:atm_decay_series:20260324`, `app:atm_anchor_diag:20260324` and cold files `data/atm_decay/atm_20260324.json`, `data/atm_decay/atm_series_20260324.jsonl`, `data/atm_decay/atm_anchor_diag_20260324.jsonl`
  - Post-restart online check: `/api/atm-decay/history -> count=0`, `/history?view=full&count=1&schema=v1 -> atm=null`, pipeline data timestamps continue advancing
  - Latest forced clean restart confirms same-day anchor capture now happens during the startup window: Redis `app:opening_atm:20260324` contains a fresh `11:32:26 ET` anchor, while `/api/atm-decay/history` still remains `count=0` and `/history` still returns `atm=null`
  - Fresh online restart on new code still produced same-day startup anchors (`11:55:46 ET`, strike `653.0`) but `/api/atm-decay/history` remained `count=0`, `/history` remained `atm=null`, and Redis still showed no `app:atm_decay_series:*` / `app:atm_anchor_diag:*` entries.
  - Fresh online restart also confirmed the new startup path still does not emit observable `[Lifespan]` startup-repair log lines in `backend_runtime.current.log`, so the remaining blocker is not trade-date capture but first-sample materialization after lock.
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> pending rerun after latest note sync

## Risks / Constraints
- Risk 1: Same-day startup now captures a fresh anchor, but the first post-lock decay point still has not been persisted, so frontend continues to show `atm=null` until that first valid sample lands.
- Risk 2: `calc_indexes()` remains price-incomplete for the anchor legs, so the new `option_quote()` repair path must remain bounded and must not regress into broad polling.

## Additional Online Findings
- The diagnostic payload includes a `failure_reasons` list so downstream analysis can distinguish which leg was non-positive.
- `SPY260324C652000.US` remains present in the live chain but continues to show `bid=0/ask=0/last_price=0` in diagnostics, while the paired put is healthy.
- `option_quote()` on the same call symbol returns a positive last price in isolated verification, proving the remaining issue is endpoint/path selection, not source data absence.
- Live restart after the WS-price guard no longer immediately fell back into a hard `source_version` plateau; sampled `store.version/source_version` advanced from `113 -> 194 -> 354` over consecutive windows.
- The old `10:56:47 ET` flat-zero ATM lock was confirmed to live in both Redis and cold JSON/JSONL persistence, which is why frontend kept restoring the same platform until the persisted state was explicitly invalidated.
- Latest live restart produced a new same-day anchor at `11:32:26 ET` (`strike=659.0`) with `series_len=0`, proving startup no longer waits for the next trade date but also proving the remaining gap is first-point persistence, not anchor capture itself.

## Next Action
- Immediate Next Step: Trace why fresh startup anchors still leave `series_len=0` / `atm=null` after immediate subscription refresh and unconditional recompute, with the strongest current hypothesis being repeated flat-zero suppression rather than `raw_pct_unavailable`.
- Owner: Codex

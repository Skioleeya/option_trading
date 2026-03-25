# Open Tasks

## Priority Queue
- [x] P1: Verify live ATM anchor diagnostics after restart when quote connectivity is healthy
  - Owner: Codex
  - Done: Healthy restart completed; persisted diagnostics confirm `SPY260324C652000.US` remains the starving leg while the paired put has positive `bid/ask/last_price`.
- [x] P1: Inspect the persisted anchor diagnostics for the exact leg that starves after lock
  - Owner: Codex
  - Done: Diagnostics plus isolated `option_quote()` verification show the call leg starves online because the live refresh path uses `calc_indexes()` rows that do not contain price fields.
- [x] P1: Add online price backfill for anchor/mandatory symbols via `option_quote()`
  - Owner: Codex
  - Done: Added bounded shared `option_quote()` repair helper, wired it into both `IVBaselineSync` batch flow and `FeedOrchestrator` tick flow, and front-loaded restored anchor symbols into `mandatory_symbols` during `lifespan` startup.
- [ ] P1: Verify the new bounded anchor price repair path in a healthy restarted backend
  - Owner: Codex
  - Definition of Done: Runtime logs show bounded repair attempts for restored/captured anchor legs, and ATM diagnostics/history show the starving leg can recover a positive price without waiting for `calc_indexes()`.
  - Blocking: Requires a healthy quote runtime restart in the current environment.
- [ ] P1: Verify opening ATM lock no longer appends a flat `0/0/0` first tick
  - Owner: Codex
  - Definition of Done: After a fresh anchor lock, `/api/atm-decay/history` does not add a new `0/0/0` row before the first real post-lock movement.
  - Blocking: Requires another live lock event after the bad-anchor invalidate + restore-discard patch.
- [ ] P1: Verify persisted flat-zero ATM anchors no longer restore into active payload after restart
  - Owner: Codex
  - Definition of Done: After deleting runtime state and restarting, `/api/atm-decay/history` remains empty and `/history` returns `atm=null` until a new clean lock is captured.
  - Blocking: Need one more short online observation window after restart.
- [ ] P1: Verify intraday startup bootstrap locks same-day ATM anchor immediately
  - Owner: Codex
  - Definition of Done: During regular session startup with no valid restored anchor, the initial `fetch_chain()` snapshot produces an ATM anchor on the same trade date without waiting for the next day.
  - Done: Forced clean restart produced a fresh same-day anchor in Redis at `2026-03-24 11:32:26 ET` with no persisted carry-over.
- [ ] P1: Verify first post-lock ATM decay sample persists after same-day startup lock. SUPERSEDED-BY: `2026-03-25/atm-decay-anchor-recapture-repair-20260325`
  - Owner: Codex
  - Definition of Done: After same-day startup captures a fresh anchor, `app:atm_decay_series:{date}` and `/api/atm-decay/history` receive the first non-flat valid point and `/history` surfaces non-null `atm`.
  - Status Note: Startup path now performs `bootstrap lock -> immediate mandatory subscription refresh -> bounded one-shot repair -> unconditional decay recompute`, but fresh online restarts at `11:50 ET` and `11:55 ET` still produced same-day anchors with `series_len=0` and `atm=null`.
  - Blocking: Remaining blocker needs deeper runtime tracing; current evidence suggests flat-zero suppression may still be consuming the first valid path without persisting history or diagnostics.
- [ ] P1: Re-run frontend ATM chart regression in an environment where Vitest can spawn `esbuild`
  - Owner: Codex
  - Definition of Done: `dashboardStore` regression test or equivalent UI check confirms flat ATM values still append new timestamps and the chart extends in time.
  - Blocking: Local `npm --prefix l4_ui run test -- dashboardStore` currently fails with `spawn EPERM`.
- [ ] P1: Restore OI continuity on Rust live path
  - Owner: Codex
  - Definition of Done: Rust-origin live path no longer leaves `oi_smooth_entries=0` under healthy startup.
  - Blocking: Must reconcile Rust producer schema with current `apply_oi_smooth()` contract

## Parking Lot
- [ ] Re-check whether `current_volume` overflow drops on ATM anchor legs are only noise or part of the price-freeze symptom.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Prevented non-positive WS quote fields from overwriting recovered positive anchor-leg prices in `ChainStateStore`, with focused regression coverage (2026-03-24 10:53 ET)
- [x] Suppressed flat post-lock opening ATM ticks from the main series until the first real move, with tracker regression coverage (2026-03-24 10:56 ET)
- [x] Discarded persisted flat-zero ATM anchors during restore/deferred-restore, added storage helper coverage, and invalidated the live `10:56:47 ET` bad anchor from Redis plus cold storage before restart (2026-03-24 11:15 ET)
- [x] Added intraday startup bootstrap lock path so same-day cold starts can capture an ATM anchor immediately from the startup snapshot, with tracker regression coverage (2026-03-24 11:21 ET)
- [x] Corrected startup bootstrap to use unfiltered L0 store snapshots plus a bounded retry window; live restart confirmed same-day anchor capture at `11:32:26 ET` without waiting for the next trade date (2026-03-24 11:33 ET)
- [x] Added startup one-shot anchor-leg repair plus immediate decay recompute after same-day bootstrap lock, with focused L0/L1 regression coverage (2026-03-24 11:52 ET)
- [x] Added immediate mandatory subscription refresh plus unconditional startup recompute after same-day bootstrap lock, with focused L0/L1 regression coverage (2026-03-24 11:57 ET)
- [x] Verified over a 20-second live window that ATM/depth profile/GEX remained valid and versions advanced, while ATM values stayed numerically flat (2026-03-24 10:35 ET)
- [x] Fixed frontend ATM history compression so same-value ticks with newer timestamps are preserved for chart progression (2026-03-24 10:38 ET)
- [x] Added bounded `option_quote()` price repair for anchor/mandatory symbols in both IV sync batches and orchestrator startup ticks (2026-03-24 11:02 ET)
- [x] Added REST price fallback in `ChainStateStore` for symbols with no valid WS price yet, with focused regression coverage (2026-03-24 10:12 ET)
- [x] Verified isolated `option_quote()` backfills `SPY260324C652000.US` into store with positive `last_price` (2026-03-24 10:12 ET)
- [x] Verified online `IVBaselineSync` still cannot repair ATM because `calc_indexes()` for the anchor legs returns no `last_done/volume/turnover` (2026-03-24 10:13 ET)
- [x] Confirmed runtime symptom is backend zero-output, not frontend field loss (2026-03-24 09:35 ET)
- [x] Identified broken OI helper path after `ChainStateStore.apply_event()` contract change (2026-03-24 09:38 ET)
- [x] Patched L0 helper OI propagation and added regression coverage (2026-03-24 09:40 ET)
- [x] Added startup-safe symbol fallback for HOT-START OI preload/update paths (2026-03-24 09:55 ET)
- [x] Added persisted ATM anchor-leg diagnostics for raw decay starvation with regression coverage (2026-03-24 10:01 ET)

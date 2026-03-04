# Legacy Backup Manifest

**Date**: 2026-03-04  
**Operator**: Antigravity (Architecture Lead)  
**Reason**: Full L0–L4 refactoring cutover complete. AgentG and legacy compute/UI layers sunset-ready.

> These files are preserved for rollback and audit. They are **NOT** in the active import graph when `USE_L2 = True` in `main.py`.

---

## `agents/` — L2 Decision Layer (replaced by `l2_refactor/`)

| File | Size | Replaced By |
|------|------|-------------|
| `agent_g.py` | 29 KB | `l2_refactor/reactor.py` (L2DecisionReactor) |
| `agent_a.py` | 4 KB | `l2_refactor/signals/momentum_signal.py` |
| `agent_b.py` | 24 KB | `l2_refactor/signals/trap_detector.py` |
| `base.py` | 1 KB | `l2_refactor/events/decision_events.py` (AgentResult) |
| `services/gamma_analyzer.py` | 11 KB | `l2_refactor/signals/` pipeline |
| `services/greeks_extractor.py` | 10 KB | `l1_refactor/aggregation/streaming_aggregator.py` |

---

## `services/analysis/` — L1 Compute Layer (replaced by `l1_refactor/`)

| File | Size | Replaced By |
|------|------|-------------|
| `bsm.py` | 7 KB | `l1_refactor/compute/compute_router.py` |
| `bsm_fast.py` | 20 KB | `l1_refactor/compute/` (Numba kernels) |
| `greeks_engine.py` | 8 KB | `l1_refactor/reactor.py` (L1ComputeReactor) |
| `depth_engine.py` | 7 KB | `l1_refactor/signals/micro_structure.py` |
| `entropy_filter.py` | 6 KB | `l0_refactor/quality/DataQualityReport` |
| `jump_detector.py` | 3 KB | `l0_refactor/sanitize/StatisticalBreaker` |
| `mtf_iv_engine.py` | 5 KB | `l2_refactor/signals/` pipeline |
| `time_decay_factor.py` | 2 KB | `l1_refactor/time/ttm_v2.py` |
| `volume_imbalance_engine.py` | 6 KB | `l1_refactor/signals/micro_flow.py` |

---

## `services/feeds/` — L0 Data Ingestion (replaced by `l0_refactor/`)

| File | Size | Replaced By |
|------|------|-------------|
| `option_chain_builder.py` | 12 KB | `l0_refactor/feeds/LongportFeedAdapter.py` |
| `market_data_gateway.py` | 8 KB | `l0_refactor/feeds/MarketFeed.py` |
| `chain_state_store.py` | 10 KB | `l0_refactor/store/MVCCChainStateStore.py` |
| `feed_orchestrator.py` | 9 KB | `l0_refactor/rate_governor/` |
| `sanitization.py` | 12 KB | `l0_refactor/sanitize/SanitizePipelineV2.py` |
| `iv_baseline_sync.py` | 14 KB | `l1_refactor/iv/iv_resolver.py` |
| `subscription_manager.py` | 9 KB | `l0_refactor/feeds/` protocol |
| `rate_limiter.py` | 4 KB | `l0_refactor/rate_governor/` (4-layer governor) |
| `tier2_poller.py` | 6 KB | Merged into L0 feed adapter |
| `tier3_poller.py` | 7 KB | Merged into L0 feed adapter |

---

## `services/flow, fusion, cache, trackers/` — L2 Internals (replaced by `l2_refactor/`)

Replaced by `l2_refactor/signals/`, `l2_refactor/fusion/`, `l2_refactor/feature_store/`.

---

## `ui/` — L3 Presenters (replaced by `l3_refactor/presenters/`)

| Directory | Replaced By |
|-----------|-------------|
| `micro_stats/` | `l3_refactor/presenters/micro_stats.py` |
| `tactical_triad/` | `l3_refactor/presenters/tactical_triad.py` |
| `wall_migration/` | `l3_refactor/presenters/wall_migration.py` |
| `depth_profile/` | `l3_refactor/presenters/depth_profile.py` |
| `active_options/` | `l3_refactor/presenters/active_options.py` |
| `mtf_flow/` | `l3_refactor/presenters/mtf_flow.py` |
| `skew_dynamics/` | `l3_refactor/presenters/skew_dynamics.py` |

---

## `main_pre_cutover.py` — Snapshot

Snapshot of `backend/app/main.py` taken after L1+L2 cutover (2026-03-04). To reverify legacy behavior, set `USE_L2 = False` in `backend/app/main.py`.

---

## NOT Backed Up (Still Active)

| Path | Reason |
|------|--------|
| `services/analysis/atm_decay_tracker.py` | Still called from `main.py` — not yet replaced |
| `config/` | Shared infrastructure — both stacks use it |
| `services/system/` | Redis, Historical store — infrastructure |
| `models/` | Shared Pydantic models |

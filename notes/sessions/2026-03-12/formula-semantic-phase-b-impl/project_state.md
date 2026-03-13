# Project State

## Snapshot
- DateTime (ET): 2026-03-12 14:50:37 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `UNVERIFIED`
  - L0-L4 Pipeline: `UNVERIFIED`

## Current Focus
- Primary Goal: Execute OpenSpec `formula-semantic-phase-b-skew-and-raw-exposure-contracts`.
- Scope In:
  - Add canonical `rr25_call_minus_put` alongside legacy `skew_25d_normalized`.
  - Add canonical `net_vanna_raw_sum` / `net_charm_raw_sum` while preserving legacy aliases.
  - Sync L1/L2/research contracts, targeted tests, SOP, and OpenSpec task tracking.
- Scope Out:
  - No L0 ingest/schema changes.
  - No L3/L4 breaking rename; legacy alias continuity remains in place.
  - No Phase D research metric expansion.

## What Changed (Latest Session)
- Files:
  - `l1_compute/aggregation/streaming_aggregator.py`
  - `l1_compute/output/enriched_snapshot.py`
  - `l1_compute/reactor.py`
  - `l1_compute/tests/test_reactor.py`
  - `l2_decision/feature_store/extractors.py`
  - `l2_decision/agents/services/gamma_qual_analyzer.py`
  - `l2_decision/agents/services/greeks_extractor.py`
  - `l2_decision/tests/test_feature_store.py`
  - `l2_decision/tests/test_gamma_qual_analyzer.py`
  - `shared/services/research_feature_store.py`
  - `l3_assembly/tests/test_research_feature_store.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
  - `docs/IV_METRICS_MAP.md`
  - `openspec/changes/formula-semantic-phase-b-skew-and-raw-exposure-contracts/tasks.md`
- Behavior:
  - L1 aggregate contracts now emit canonical `net_vanna_raw_sum` / `net_charm_raw_sum` and keep `net_vanna` / `net_charm` as compatibility aliases.
  - L2 feature extraction now emits canonical `rr25_call_minus_put` while retaining `skew_25d_normalized = (put_iv - call_iv) / atm_iv`.
  - Gamma qualitative services and research storage now read canonical raw-sum fields first and backfill legacy aliases for downstream continuity.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_reactor.py l2_decision/tests/test_feature_store.py l2_decision/tests/test_gamma_qual_analyzer.py l3_assembly/tests/test_research_feature_store.py`
  - Result: `74 passed`

## Risks / Constraints
- Risk 1: L3/UI consumers still read legacy `net_charm` naming, so Phase B keeps alias continuity instead of forcing a downstream rename.
- Risk 2: Working tree contains many unrelated user/runtime changes; this session only touched Phase B contract files and session/context records.

## Next Action
- Immediate Next Step: Decide whether Phase D should consume official LongPort `historical_volatility/premium/standard` fields before adding new derived research vol metrics.
- Owner: Codex / next implementing agent

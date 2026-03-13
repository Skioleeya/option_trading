# Project State

## Snapshot
- DateTime (ET): 2026-03-12 10:49:33 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 统一 GEX/Wall 口径并修复 `flip_level` 语义偏差。
- Scope In: L1 GEX 聚合与 legacy 聚合一致性、L1 flip_level 算法、L2 `net_gex_normalized`、对应测试与 SOP。
- Scope Out: 引入 OMM 净仓位数据源、L3/L4 展示逻辑改版。

## What Changed (Latest Session)
- Files:
  - `l1_compute/analysis/bsm_fast.py`
  - `l1_compute/aggregation/streaming_aggregator.py`
  - `l1_compute/output/enriched_snapshot.py`
  - `l2_decision/feature_store/extractors.py`
  - `l1_compute/tests/test_compute.py`
  - `l1_compute/tests/test_streaming_aggregator.py`
  - `l2_decision/tests/test_feature_store.py`
  - `l2_decision/tests/test_gamma_qual_analyzer.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
- Behavior:
  - `total_put_gex` 在 L1/legacy 聚合口径统一为非负幅度值（MMUSD），`net_gex = total_call_gex - total_put_gex`。
  - `flip_level` 从“邻接变号”改为“按 strike 排序后的 cumulative net GEX 首次过零（支持线性插值）”。
  - `net_gex_normalized` 从 `/1e9` 修正为 `/1000`（`net_gex` 输入单位 MMUSD）。
- Verification:
  - `scripts/test/run_pytest.ps1 l1_compute/tests/test_compute.py l1_compute/tests/test_streaming_aggregator.py l1_compute/tests/test_reactor.py l2_decision/tests/test_feature_store.py l2_decision/tests/test_gamma_qual_analyzer.py`
  - 结果：89 passed / 0 failed

## Risks / Constraints
- Risk 1: `net_gex_normalized` 量纲修正后，依赖该特征的线上阈值敏感度会发生变化（已通过现有回归，仍需盘中观察）。
- Risk 2: 历史离线分析若混用旧口径与新口径，需要按会话分界做再归一。

## Next Action
- Immediate Next Step: 盘中观察 `net_gex_normalized` 阈值敏感度与 flip_level 新语义稳定性。
- Owner: Codex

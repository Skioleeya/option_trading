# Project State

## Snapshot
- DateTime (ET): 2026-03-09 14:40:22 -04:00
- Branch: master
- Last Commit: 1a72132
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 修复 IV SKEW 在 L0->L4 链路常态为 0 的问题，落地真25Δ口径并补齐 UI 不可计算态。
- Scope In:
  - L1 输出补充 `computed_delta`。
  - L2 skew 特征改为真25Δ（delta 最近邻）并新增 `skew_25d_valid`。
  - L3 依据 `skew_25d_valid` 输出 `UNAVAILABLE`，并修正默认阈值语义。
  - L4 回归测试覆盖 `N/A` 中性色渲染契约。
  - 配置默认阈值与 SOP 同步。
- Scope Out:
  - 不改 Rust runtime path。
  - 不改 L2 融合/护栏策略。
  - 不改全局亚洲盘红涨绿跌视觉规范。

## What Changed (Latest Session)
- Files:
  - l1_compute/reactor.py
  - l1_compute/tests/test_arrow.py
  - l2_decision/feature_store/extractors.py
  - l2_decision/tests/test_feature_store.py
  - l3_assembly/assembly/ui_state_tracker.py
  - l3_assembly/presenters/ui/skew_dynamics/mappings.py
  - l3_assembly/presenters/ui/skew_dynamics/presenter.py
  - l3_assembly/tests/test_ui_state_tracker.py
  - l3_assembly/tests/test_presenters.py
  - l3_assembly/tests/test_reactor.py
  - l4_ui/src/components/__tests__/skewDynamics.model.test.ts
  - l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx
  - shared/config/agent_b.py
  - shared/config_cloud_ref/market_structure.py
  - docs/SOP/L2_DECISION_ANALYSIS.md
- Behavior:
  - L1 Arrow `RecordBatch` 新增 `computed_delta` 字段并向下游透传。
  - L2 `skew_25d_normalized` 改为真25Δ算法：CALL(+0.25)/PUT(-0.25) 最近邻，容差 ±0.10。
  - L2 新增 `skew_25d_valid`（1/0），样本不足或超容差不再伪造 `0.0`。
  - L3 在 `skew_25d_valid=0` 时输出 `UNAVAILABLE`，UI 值走 `N/A`。
  - 默认阈值更新为 `skew_speculative_max=-0.10`、`skew_defensive_min=0.15`。
- Verification:
  - 后端定向回归通过（72 passed）。
  - 前端定向 vitest 通过（2 files, 5 tests）。

## Risks / Constraints
- Risk 1: 现有 `l3_assembly/tests/test_presenters.py` 的 `TestDepthProfilePresenterV2::test_no_nan_inf_in_gex` 与本次改动无关但仍失败（字段断言历史问题）。
- Risk 2: 未执行全量 E2E 实盘链路联调（本次聚焦 IV skew 契约修复）。

## Next Action
- Immediate Next Step: 合并后在实盘运行环境观察 `ui_state.skew_dynamics` 的 `UNAVAILABLE` 比例与有效样本稳定性。
- Owner: Codex/User

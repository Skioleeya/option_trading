PARENT_CHANGE_ID: impl-20260416-mm-rust-cutover-parent
DEPENDENCY_ORDER: 2
BLOCKED_BY: impl-20260416-mm-rust-cutover-wave1-l0-condition-and-mm-core

## Why

Wave1 已完成 L0 条件字段贯通与 Rust MM 核心函数，但 L1/L2 生产链路尚未把机构化 MM 指标纳入标准 contract。Wave2 目标是在不破坏层边界前提下，把 Rust owner 的 MM 快照聚合指标注入 L1 `extra_metadata`，并在 L2 `feature_vector` 与 `DecisionOutput.data.fused_signal` 中稳定输出。

## What Changes

1. 新增 Rust `mm_snapshot_metrics` 聚合函数（snapshot-level）并注册到 `shared_rust.services`。
2. `app/loops` 增加薄封装模块，将 L0 snapshot 链数据委托 Rust 计算后落入 `extra_metadata.mm_flow_metrics`。
3. L2 feature store 增加 MM 特征提取（net delta/gamma、OI participation、suppression bias、tick-rule/condition/spread counters）。
4. `DecisionOutput.data.fused_signal` 增加 `mm_flow` 字段，把 L2 特征透传给 L3 payload。
5. SOP 同步 L1/L2 新合同字段。

## Scope

In:
- `shared_rust_services/src/mm_flow.rs`
- `app/loops/{mm_flow_metadata.py,compute_metadata.py}`
- `l2_decision/feature_store/*`
- `l2_decision/events/decision_events.py`
- `docs/SOP/{L1_LOCAL_COMPUTATION.md,L2_DECISION_ANALYSIS.md}`

Out:
- L3 presenter 层新增视觉解释逻辑（Wave3）
- 逐笔 multi-leg 50ms 匹配器（当前仅 snapshot 近似聚类）

## Field Contract (Wave2)

- `extra_metadata.mm_flow_metrics`
- `feature_vector.net_delta_exposure_live`
- `feature_vector.net_gamma_exposure_live`
- `feature_vector.residual_delta_after_netting`
- `feature_vector.oi_participation_ratio_live`
- `feature_vector.flow_suppression_bias`
- `feature_vector.flow_dominance_ratio`
- `feature_vector.midpoint_tickrule_count`
- `feature_vector.condition_filtered_count`
- `feature_vector.complex_spread_count`
- `agent_g.data.fused_signal.mm_flow.*`

## Verification Gate

1. Rust `mm_snapshot_metrics` 可导入并返回稳定字段。
2. L1 metadata、L2 feature、DecisionOutput `mm_flow` 单测通过。
3. strict validate 通过。

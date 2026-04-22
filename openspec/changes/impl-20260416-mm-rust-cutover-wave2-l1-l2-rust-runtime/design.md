## Context

Wave2 聚焦“合同贯通”，不是 UI 展示重构。关键是把 Rust owner 计算结果通过最短链路注入 L2 决策输入，并保证低耦合。

## Design

1. Rust owner:
   - 在 `mm_flow.rs` 内新增 `mm_snapshot_metrics(chain_rows)`。
   - 输入为 snapshot 行集合，输出标准 dict（delta/gamma/OI/side-pressure/counter metrics）。
2. L1 metadata bridge:
   - Python 仅做薄封装：`app/loops/mm_flow_metadata.py`。
   - `compute_metadata._build_l1_extra_metadata()` 注入 `mm_flow_metrics`。
3. L2 extraction:
   - `extractors_common` 增加 metadata 读取 helper。
   - MM 特征独立拆分到 `extractors_mm_flow.py`。
   - VRP/impact 构建拆分到 `extractors_vrp_impact.py`，降低 registry 文件耦合和长度。
4. L2 output contract:
   - `DecisionOutput.data.fused_signal.mm_flow` 统一透传特征值。

## Contract Consistency Check

1. OpenSpec Field Contract
2. `extra_metadata.mm_flow_metrics` keys
3. `FeatureVector` keys
4. `DecisionOutput.data.fused_signal.mm_flow` keys

## Purpose

在 Wave2 内将 MM 机构化快照指标贯通到 L1/L2 生产 contract，并通过 L2 fused_signal 稳定透传。

## Requirements

### Requirement: Rust Must Own Snapshot MM Aggregation

MM 快照聚合必须由 Rust owner 执行，Python 仅允许薄封装。

#### Scenario: Build MM Metrics From L0 Snapshot Rows

WHEN compute loop 处理 L0 snapshot
THEN 必须通过 `shared_rust.services.mm_snapshot_metrics` 生成指标
AND 结果必须落入 `extra_metadata.mm_flow_metrics`。

### Requirement: L2 Feature Vector Must Include MM Fields

L2 特征层必须稳定输出 MM 关键字段。

#### Scenario: FeatureStore Computes One Tick

WHEN `FeatureStore.compute_all()` 被调用
THEN `feature_vector` 必须包含 net delta/gamma、OI participation、suppression、tick-rule/condition/spread 计数等字段
AND 缺失值必须回落到 `0.0`。

### Requirement: DecisionOutput Must Expose MM Flow

L2 输出契约必须向下游透传 MM 字段。

#### Scenario: DecisionOutput Data Is Read By L3

WHEN 读取 `DecisionOutput.data`
THEN `fused_signal.mm_flow` 必须存在
AND 包含 Wave2 合同字段集合。

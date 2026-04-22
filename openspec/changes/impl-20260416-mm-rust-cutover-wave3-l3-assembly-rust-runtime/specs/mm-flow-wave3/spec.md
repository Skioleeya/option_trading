## Purpose

定义 Wave3 的 L3 合同增强：将 MM 指标作为稳定 payload/delta 字段输出。

## Requirements

### Requirement: L3 Full Payload Must Expose MM Flow

#### Scenario: FrozenPayload Is Serialized

WHEN `FrozenPayload.to_dict()` 被调用
THEN 输出必须包含 `agent_g.data.mm_flow`
AND 在显式 `mm_flow` 缺失时必须回退到 `fused_signal.mm_flow`。

### Requirement: L3 Delta Must Carry MM Flow Diff

#### Scenario: MM Flow Changes Between Two Payloads

WHEN `FieldDeltaEncoder` 生成 DELTA 消息
THEN `changes.agent_g_data.mm_flow` 必须包含最新值。

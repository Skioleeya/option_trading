## Context

L3 是 contract assembly 层，目标是稳定输出而非重算。Wave3 只补齐显式合同，不新增跨层计算。

## Design

1. `FrozenPayload.mm_flow`:
   - 新增可选字段。
   - 序列化时优先用显式值；若缺失则回退 `fused_signal.mm_flow`。
2. Delta path:
   - `FieldDeltaEncoder` 在 `agent_g_data` 里单独输出 `mm_flow` 变更。
3. Compatibility:
   - 保持已有 `fused_signal` 原样输出，`mm_flow` 为增强字段，不破坏旧消费方。

## Contract Consistency Check

1. L2 输出：`DecisionOutput.data.fused_signal.mm_flow`
2. L3 full：`agent_g.data.mm_flow`
3. L3 delta：`changes.agent_g_data.mm_flow`

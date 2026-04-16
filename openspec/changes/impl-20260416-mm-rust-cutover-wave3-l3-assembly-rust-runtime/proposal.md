PARENT_CHANGE_ID: impl-20260416-mm-rust-cutover-parent
DEPENDENCY_ORDER: 3
BLOCKED_BY: impl-20260416-mm-rust-cutover-wave2-l1-l2-rust-runtime

## Why

Wave2 已把 MM 指标落入 L2 `fused_signal.mm_flow`，但 L3 payload/delta 合同仍未提供显式稳定透传字段。Wave3 需要在不破坏层边界的前提下，形成 `agent_g.data.mm_flow` 稳定输出与增量同步语义。

## What Changes

1. L3 `FrozenPayload` 增加 `mm_flow` 合同字段（可选），并在序列化时默认从 `fused_signal.mm_flow` 回填。
2. L3 delta encoder 增量通道增加 `agent_g_data.mm_flow` 变更输出。
3. 新增 L3 合同测试，覆盖 full payload 与 delta 两条路径。
4. 更新 L3 SOP 文档，明确 `agent_g.data.mm_flow` 字段语义。

## Scope

In:
- `l3_assembly/events/payload_events.py`
- `l3_assembly/assembly/delta_encoder.py`
- `l3_assembly/events/test_payload_mm_flow_contract.py`
- `l3_assembly/assembly/test_delta_encoder_mm_flow.py`
- `docs/SOP/L3_OUTPUT_ASSEMBLY.md`

Out:
- L4 组件消费策略与视觉映射（由后续 UI 会话处理）

## Verification Gate

1. L3 合同测试通过（payload + delta）。
2. strict validate 通过。
3. 文件长度与层边界门禁通过。

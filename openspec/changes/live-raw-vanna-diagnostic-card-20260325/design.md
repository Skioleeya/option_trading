## Design

### 1. L3 Transport Choice

不新增顶层 payload 字段，也不扩大 `ui_state` typed presenter 合同。`net_vanna_raw_sum` 通过现有 `agent_g.data.micro_structure.micro_structure_state` 诊断通道透传。

这样可以复用现有：

- `FrozenPayload.to_dict()` 中的 `micro_structure`
- `FieldDeltaEncoder` 的 `agent_g_data.micro_structure` diff
- L4 store / delta merge 的泛型 spread 行为

### 2. Canonical Source Rule

L3 `UIStateTracker` 必须优先读取 canonical `aggregates.net_vanna_raw_sum`，仅在兼容场景下回退 `aggregates.net_vanna`。

### 3. L4 Rendering Rule

Right Panel 新增独立 `RAW VANNA` 卡片：

- 主值显示 compact signed value
- 次级行显示 exact signed raw sum
- 状态仅表达 `POSITIVE / NEGATIVE / FLAT / UNAVAILABLE`

该卡片属于 diagnostic view，不重写 TacticalTriad 的 `S-VOL` 语义。

## Why

盘后联查发现 `dashboard_delta` 传输链路仍然存活，但绝大多数帧只携带 `heartbeat_timestamp`。这说明 transport 没断，真正缺的是一个能直接暴露 canonical raw vanna 的 live 诊断位，便于区分“链路活着”与“指标确实在刷新”。

当前 `net_vanna_raw_sum` 只在 L1/L2 canonical 字段与 research/debug 路径中可见，L3/L4 live 面板没有一个直接可视化出口。

## What Changes

1. 在 L3 复用现有 `agent_g.data.micro_structure` 诊断通道，透传 `micro_structure_state.net_vanna_raw_sum`。
2. 在 L4 Right Panel 增加独立 `RAW VANNA` 数字卡片，直接显示 canonical raw sum。
3. 明确 delta 观察口径：heartbeat-only `dashboard_delta` 代表链路活性，不代表指标重算。

## Impact

- 提供 raw Greek canonical 字段的 live 可视性，不改变 TacticalTriad / MicroStats 既有契约。
- 维持现有 `agent_g.data` / `agent_g_data` delta contract，不新增 transport 特例。
- 让盘后/停滞时段更容易区分“数据没变”和“链路挂了”。

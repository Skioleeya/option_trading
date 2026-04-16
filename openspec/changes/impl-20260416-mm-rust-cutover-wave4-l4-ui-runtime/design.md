## Context

Wave4 只处理 L4 消费与展示，不允许把 MM 指标计算逻辑引入前端。目标是通过 model 层完成合同归一化，组件层只做视觉呈现。

## Design

1. 读取优先级
   - 一级：`agent_g.data.mm_flow`
   - 二级：`agent_g.data.fused_signal.mm_flow`
2. 归一化策略
   - 非有限数值统一回落 `0`
   - direction 仅由 `flow_dominance_ratio` 映射为 `SUPPRESSIVE/EXPANSIVE/BALANCED`
3. 边界约束
   - `MmFlowCard` 不直接读取跨层模块，仅依赖 `dashboardStore` selector 或 stable props
   - `rightPanelModel` 保持 typed contract 汇总，不新增跨组件共享状态

## Consistency Rule

`OpenSpec spec`、`L4 model 字段键` 与 `UI 展示项` 必须一一对应，禁止新增未定义字段或在组件层隐式重命名。

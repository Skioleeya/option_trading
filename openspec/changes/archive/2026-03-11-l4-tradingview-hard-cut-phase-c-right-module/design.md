## Context

Right 模块对合同稳定性敏感，尤其是 `ActiveOptions` 的槽位稳定、方向语义和占位行为。硬切期间必须避免与其他模块耦合提交。

## Decisions

1. Right 组件只消费 model 层产物，不直接解析原始 payload。
2. `ActiveOptions` 固定 5 行槽位，缺项补占位且保持 `slot_index` 稳定键。
3. FLOW 颜色只跟随 `flow` 数值符号，不信任后端文本方向字段。
4. Right 模块开关化，支持独立灰度与回退。

## Boundary Constraints

- 禁止改动 Center 图表交互和 Left 面板实现。
- 禁止引入反向依赖和跨层私有成员访问。
- 禁止在 Right 子提案中嵌套其他模块交付内容。

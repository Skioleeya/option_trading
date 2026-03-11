## Context

Center 当前已具备 Focus+Context 与 strict-hit 语义，但图表实现仍与组件耦合较深，硬切过程中不利于引擎边界管理和回退控制。

## Decisions

1. 以适配器驱动图表生命周期（创建、更新、销毁、异常降级）。
2. 保持 ET `09:30-16:00` 窗口和 strict-hit 交互语义不变。
3. 保留“增量优先、全量回退”的双路径更新策略。
4. 失败可降级：图表失败不应中断 store 更新与其余面板渲染。

## Boundary Constraints

- 禁止引入 Right/Left 模块实现改动。
- 禁止 Center 对具体网络协议层私有实现产生依赖。
- 禁止任何反向依赖或跨层私有成员访问。

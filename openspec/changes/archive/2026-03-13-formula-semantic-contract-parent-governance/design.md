## Context

本次整改不是单点 bug fix，而是“公式语义治理”。风险主要来自：

- 运行时字段仍被真实消费，不能粗暴改名；
- 现有测试已把部分历史口径固化；
- 审计文档要求明确区分 `academic standard`、`proxy`、`heuristic`。

因此必须拆成阶段化子提案，先止血，再收敛合同，再补 provenance，最后做研究增强。

## Decisions

1. 父提案只做治理，不承载运行时代码实现。
2. 子提案顺序固定为：
   - A: `VRP` 单位与 `GEX proxy` 语义止血
   - B: `RR25 / raw Greek sum` 合同收敛
   - C: provenance registry 与启发式公式标注
   - D: 研究增强字段引入
3. Phase B 若涉及字段改名，必须采用“新增 canonical 字段 + 兼容 alias 保留一阶段”策略。
4. 所有阶段都必须同步相关 SOP 与 handoff debt 记录。

## Boundary Constraints

- 禁止 `l2_decision -> l3_assembly/l4_ui` 新依赖。
- 禁止在 L3/L4 写死学术语义补丁，语义源必须来自 L1/L2/shared 中立合同。
- 禁止在父提案中打包实现多个阶段的运行时代码。

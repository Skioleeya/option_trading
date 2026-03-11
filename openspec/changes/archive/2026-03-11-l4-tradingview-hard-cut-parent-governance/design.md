## Context

当前 L4 已采用 `ProtocolAdapter -> DashboardStore -> Panels` 结构，且中心图表为 `lightweight-charts`。本次硬切要求在不破坏 L0-L4 合同语义前提下，按模块逐步切换并保持可回退。

## Goals

- 分阶段推进硬切，避免一次性高风险替换。
- 保证模块解耦，不引入嵌套依赖链。
- 全程满足单向依赖与 strict 流程门禁。

## Non-Goals

- 不修改 L3 payload wire schema。
- 不引入 `l2 -> l3/l4` 或 `l3 -> l4` 反向依赖。

## Parent Controls

1. **Dependency Lock**: 必须按 `A(Foundation) -> B(Center) -> C(Right) -> D(Left)` 顺序执行。
2. **Module Lock**: 每个子提案只允许一个主模块目标，禁止同提案内跨模块嵌套实施。
3. **Boundary Lock**: 全链路禁止反向依赖与跨层私有成员访问。
4. **Contract Lock**: `timestamp/data_timestamp`、`rust_active`、`shm_stats` 语义保持不变。
5. **Completion Lock**: 仅当全部子提案完成且 strict 验证有证据时，父提案才可归档。

## Risk Controls

- 若出现反向依赖扫描命中，阻断子提案完成。
- 若出现 L4 广播连续性回归，阻断后续阶段。
- 若 strict gate 失败，父提案保持打开状态。

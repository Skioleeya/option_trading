## Why

`docs/OPTION_PAPER_FORMULA_AUDIT_2024_2026.md` 与 `docs/OPTION_PAPER_FORMULA_SOURCEBOOK_2024_2026.md` 已确认仓库当前同时存在三类问题：

1. 单位/符号口径冲突会直接污染 L2 决策与 L3/L4 展示解释。
2. 多个字段实际是 `proxy / heuristic`，但注释、模型说明、UI 语义仍容易被误读成学术标准或 dealer truth。
3. 部分字段需要兼容保留，不能在一个变更里混合“止血修正”和“研究升级”。

若不采用父提案 + 子提案治理，极易在同一批改动里混入合同更名、文档修辞、研究增强和测试补丁，导致边界漂移与验收失焦。

## What Changes

本父提案只治理执行顺序与门禁，不直接实现运行时代码：

1. 固化按优先级推进的四个子提案：`A -> B -> C -> D`。
2. Phase A 只处理 `P0` 语义止血：`VRP` 单位与 `GEX proxy` 表述。
3. Phase B 只处理 `P0/P1` 合同收敛：`skew_25d_*`、`net_vanna/net_charm` 命名与兼容字段。
4. Phase C 只处理 `P1` provenance 治理：`FLOW_D/E/G` 与 wall/flip 术语降级为 `proxy/heuristic`。
5. Phase D 只处理 `P2` 研究增强：双轨 `RR25` 与 realized-vol based `VRP` 升级。

## Scope

- OpenSpec 治理边界、依赖顺序、回滚条件、收口门禁。
- 不在父提案内直接提交 L0/L1/L2/L3/L4 运行时代码。

## Child Proposals

- `formula-semantic-phase-a-vrp-gex-stopgap`
- `formula-semantic-phase-b-skew-and-raw-exposure-contracts`
- `formula-semantic-phase-c-provenance-and-heuristic-labels`
- `formula-semantic-phase-d-research-metric-upgrades`

## Rollback

任一子提案若触发以下任一条件，立即停止后续阶段并回退到上一个已验证子提案：

- L0-L4 合同字段破坏兼容
- `scripts/validate_session.ps1 -Strict` 失败
- `gamma/dealer/VRP/RR25` 语义出现新旧混写
- 新字段进入主链但缺少测试与 SOP 同步

## Why

旧 `formula-semantic-phase-c-provenance-and-heuristic-labels` 定义了方向，但没有真正落地：

- 缺少 machine-readable provenance registry
- `FLOW_D/E/G` docstring 仍容易被读成 academic exact formula
- `call_wall / put_wall / flip_level_cumulative` 在 L1/L2 关键导出点仍缺统一 proxy 术语

需要一个新的 residual child，把 provenance 变成可测试合同，并让后续文档与服务引用同一个中立源。

## What Changes

1. 新增 `shared/contracts/metric_semantics.py`
2. 为关键公式指标登记 `classification / unit / sign_convention / data_prerequisites / canonical_description / live_usage`
3. 修改 `FLOW_D/E/G` 说明文字为 `research heuristic / public-data proxy`
4. 在 L1/L2 关键导出点统一加入 wall/flip 的 `trading-practice proxy` 语义
5. SOP / operator-facing docs 改为引用 registry 作为 runtime semantics source-of-truth

## Scope

- shared contracts registry
- active options flow engine docstrings
- L1/L2 proxy terminology
- SOP / operator-facing formula docs

## Parent

- `formula-semantic-followup-parent-governance`

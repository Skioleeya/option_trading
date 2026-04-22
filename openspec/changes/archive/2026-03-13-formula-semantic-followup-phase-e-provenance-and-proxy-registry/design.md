## Context

当前 provenance 信息分散在：

- 审计文档
- flow engine 顶部 docstring
- 少量 L1/L2 注释
- SOP 片段说明

这种散布状态无法防止后续实现者重新把 proxy / heuristic 写成 dealer truth 或 academic standard。

## Decisions

1. 新增中立 registry `shared/contracts/metric_semantics.py`
2. 每个登记项至少包含：
   - `metric_name`
   - `classification`
   - `unit`
   - `sign_convention`
   - `data_prerequisites`
   - `canonical_description`
   - `live_usage`
3. `FLOW_D/E/G` 顶部说明改为引用 registry，不再直接给“论文 exact 公式”暗示
4. `call_wall / put_wall / flip_level_cumulative` 统一降级为 `trading-practice proxy`

## Test Plan

- 新增 `shared/tests/test_metric_semantics.py`
- 更新 `shared/services/active_options/test_runtime_service.py`
- smoke 检查 L1/L2 关键 docstring/注释已完成 proxy wording

## Context

当前 provenance 信息散落在：

- 审计文档
- flow engine docstring
- SOP 说明
- 少量测试与注释

这会导致后续实现者在只看局部文件时重新引入“dealer truth”或“academic standard”误读。

## Decisions

1. 新增中立 registry `shared/contracts/metric_semantics.py`，避免将语义治理绑死在 L1/L2/L3 任一层。
2. 每个登记项至少包含：
   - `metric_name`
   - `classification` (`academic_standard|proxy|heuristic`)
   - `unit`
   - `sign_convention`
   - `data_prerequisites`
   - `canonical_description`
3. Flow engine docstring 改为引用 registry，而不是直接宣称论文公式。
4. wall/flip/gex 相关服务输出继续沿用现字段名，但展示和文档统一读取 registry 语义。

## File-Level Plan

1. 新增 [metric_semantics.py](e:/US.market/Option_v3/shared/contracts/metric_semantics.py)
2. 修改 [flow_engine_d.py](e:/US.market/Option_v3/shared/services/active_options/flow_engine_d.py)、[flow_engine_e.py](e:/US.market/Option_v3/shared/services/active_options/flow_engine_e.py)、[flow_engine_g.py](e:/US.market/Option_v3/shared/services/active_options/flow_engine_g.py)
   - 降级表述
   - 指向 provenance registry
3. 修改 [streaming_aggregator.py](e:/US.market/Option_v3/l1_compute/aggregation/streaming_aggregator.py) 与 [greeks_extractor.py](e:/US.market/Option_v3/l2_decision/agents/services/greeks_extractor.py)
   - 增加 proxy 术语说明

## Test Plan

- 新增建议测试：[shared/tests/test_metric_semantics.py](e:/US.market/Option_v3/shared/tests/test_metric_semantics.py)
  - 验证关键指标均已登记 provenance
- 更新 [test_runtime_service.py](e:/US.market/Option_v3/shared/services/active_options/test_runtime_service.py)
  - 确保 flow 数值展示不受 provenance 说明变更影响

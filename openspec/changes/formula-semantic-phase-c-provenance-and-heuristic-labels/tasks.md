## 1. Provenance Registry

- [ ] 1.1 新增 [metric_semantics.py](e:/US.market/Option_v3/shared/contracts/metric_semantics.py)。
- [ ] 1.2 为 `GEX / wall / zero-gamma / skew / VRP / FLOW_D/E/G` 填充 provenance 条目。
- [ ] 1.3 为 registry 增加只读访问接口，供文档/服务引用。

## 2. Heuristic Label Cleanup

- [ ] 2.1 修改 [flow_engine_d.py](e:/US.market/Option_v3/shared/services/active_options/flow_engine_d.py) docstring：从“论文公式”改为 `research heuristic / public-data proxy`。
- [ ] 2.2 修改 [flow_engine_e.py](e:/US.market/Option_v3/shared/services/active_options/flow_engine_e.py) docstring：去掉“统一学术支持”表述。
- [ ] 2.3 修改 [flow_engine_g.py](e:/US.market/Option_v3/shared/services/active_options/flow_engine_g.py) docstring：明确 `ΔOI` 合成是工程 proxy。
- [ ] 2.4 在 [streaming_aggregator.py](e:/US.market/Option_v3/l1_compute/aggregation/streaming_aggregator.py) 与 [greeks_extractor.py](e:/US.market/Option_v3/l2_decision/agents/services/greeks_extractor.py) 同步 wall/flip proxy 说明。

## 3. Verification

- [ ] 3.1 新增 [shared/tests/test_metric_semantics.py](e:/US.market/Option_v3/shared/tests/test_metric_semantics.py)。
- [ ] 3.2 更新 [test_runtime_service.py](e:/US.market/Option_v3/shared/services/active_options/test_runtime_service.py)。
- [ ] 3.3 通过 `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py shared/tests/test_metric_semantics.py`。

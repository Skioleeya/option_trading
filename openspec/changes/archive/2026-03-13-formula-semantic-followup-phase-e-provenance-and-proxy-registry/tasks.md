## 1. Registry

- [x] 1.1 新增 `shared/contracts/metric_semantics.py`
- [x] 1.2 为 `net_gex / zero_gamma_level / call_wall / put_wall / flip_level_cumulative / FLOW_D / FLOW_E / FLOW_G / vol_risk_premium / guard_vrp_proxy_pct / skew_25d_normalized / rr25_call_minus_put / net_charm_raw_sum / net_vanna_raw_sum` 建立条目
- [x] 1.3 提供只读 lookup 接口供文档/服务引用

## 2. Runtime Wording Cleanup

- [x] 2.1 修改 `FLOW_D/E/G` docstring 为 heuristic / proxy 表述
- [x] 2.2 在 `streaming_aggregator.py` 与 `greeks_extractor.py` 明确 wall/flip proxy 术语
- [x] 2.3 更新至少一个 SOP / operator-facing 文档，使 runtime semantics source 指向 registry

## 3. Verification

- [x] 3.1 新增 `shared/tests/test_metric_semantics.py`
- [x] 3.2 更新 `shared/services/active_options/test_runtime_service.py`
- [x] 3.3 通过 `scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py shared/tests/test_metric_semantics.py`


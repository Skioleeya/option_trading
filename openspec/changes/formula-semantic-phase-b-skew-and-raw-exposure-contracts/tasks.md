## 1. 25Δ Skew Contract

- [x] 1.1 在 [extractors.py](e:/US.market/Option_v3/l2_decision/feature_store/extractors.py) 保留 `skew_25d_normalized`，并新增 `rr25_call_minus_put`。
- [x] 1.2 在 `FeatureSpec.description` 中明确 `skew_25d_normalized = (put_iv - call_iv) / atm_iv`。
- [x] 1.3 在 SOP 中明确两者的符号约定与用途边界。

## 2. Raw Greek Sum Contract

- [x] 2.1 在 [streaming_aggregator.py](e:/US.market/Option_v3/l1_compute/aggregation/streaming_aggregator.py) 新增 `net_vanna_raw_sum`、`net_charm_raw_sum`。
- [x] 2.2 在 [enriched_snapshot.py](e:/US.market/Option_v3/l1_compute/output/enriched_snapshot.py) 与 [reactor.py](e:/US.market/Option_v3/l1_compute/reactor.py) 同时输出新旧字段。
- [x] 2.3 在 [gamma_qual_analyzer.py](e:/US.market/Option_v3/l2_decision/agents/services/gamma_qual_analyzer.py)、[greeks_extractor.py](e:/US.market/Option_v3/l2_decision/agents/services/greeks_extractor.py)、[research_feature_store.py](e:/US.market/Option_v3/shared/services/research_feature_store.py) 优先使用 canonical raw-sum 字段。

## 3. Verification

- [x] 3.1 更新 [test_feature_store.py](e:/US.market/Option_v3/l2_decision/tests/test_feature_store.py)。
- [x] 3.2 更新 [test_reactor.py](e:/US.market/Option_v3/l1_compute/tests/test_reactor.py)。
- [x] 3.3 更新 [test_gamma_qual_analyzer.py](e:/US.market/Option_v3/l2_decision/tests/test_gamma_qual_analyzer.py)。
- [ ] 3.4 通过 `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_reactor.py l2_decision/tests/test_feature_store.py l2_decision/tests/test_gamma_qual_analyzer.py`。

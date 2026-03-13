## 1. Dual-Track Skew

- [x] 1.1 在 [extractors.py](e:/US.market/Option_v3/l2_decision/feature_store/extractors.py) 引入 `rr25_call_minus_put` 的 research/optional path。
- [x] 1.2 在 [research_feature_store.py](e:/US.market/Option_v3/shared/services/research_feature_store.py) 增加 `rr25_call_minus_put` 列。

## 2. Dual-Track VRP

- [x] 2.1 新增 [realized_volatility.py](e:/US.market/Option_v3/shared/services/realized_volatility.py)。
- [x] 2.2 在 [extractors.py](e:/US.market/Option_v3/l2_decision/feature_store/extractors.py) 增加 `vrp_realized_based`。
- [x] 2.3 在研究文档与 SOP 中明确 `vol_risk_premium` 与 `vrp_realized_based` 的边界。

## 3. Verification

- [x] 3.1 新增 [shared/tests/test_realized_volatility.py](e:/US.market/Option_v3/shared/tests/test_realized_volatility.py)。
- [x] 3.2 更新 [test_feature_store.py](e:/US.market/Option_v3/l2_decision/tests/test_feature_store.py)。
- [x] 3.3 通过 `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l2_decision/tests/test_feature_store.py shared/tests/test_realized_volatility.py l3_assembly/tests/test_research_feature_store.py`。

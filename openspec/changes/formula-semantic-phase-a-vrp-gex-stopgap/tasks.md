## 1. VRP Unit Stopgap

- [ ] 1.1 在 [extractors.py](e:/US.market/Option_v3/l2_decision/feature_store/extractors.py) 统一 `vol_risk_premium` 的 `% points` 计算与描述。
- [ ] 1.2 在 [tactical_triad_logic.py](e:/US.market/Option_v3/shared/system/tactical_triad_logic.py) 固化 `vrp_baseline_hv` 标准化规则。
- [ ] 1.3 在 [agent_g.py](e:/US.market/Option_v3/shared/config/agent_g.py) 明确 `vrp_baseline_hv` 默认值和 guard 阈值解释。

## 2. GEX Proxy Semantics

- [ ] 2.1 在 [microstructure.py](e:/US.market/Option_v3/shared/models/microstructure.py) 修正 `200M/1000M` 旧注释。
- [ ] 2.2 在 [enriched_snapshot.py](e:/US.market/Option_v3/l1_compute/output/enriched_snapshot.py) 和 [gamma_qual_analyzer.py](e:/US.market/Option_v3/l2_decision/agents/services/gamma_qual_analyzer.py) 增补 `OI-based proxy` 说明。
- [ ] 2.3 在 SOP 中统一 `net_gex`、`zero_gamma_level`、`call_wall/put_wall` 的 proxy 表述。

## 3. Verification

- [ ] 3.1 更新 [test_feature_store.py](e:/US.market/Option_v3/l2_decision/tests/test_feature_store.py)。
- [ ] 3.2 更新 [test_reactor_and_guards.py](e:/US.market/Option_v3/l2_decision/tests/test_reactor_and_guards.py)。
- [ ] 3.3 通过 `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l2_decision/tests/test_feature_store.py l2_decision/tests/test_reactor_and_guards.py l2_decision/tests/test_gamma_qual_analyzer.py`。

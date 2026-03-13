## Context

当前 `vol_risk_premium` 由 [extractors.py](e:/US.market/Option_v3/l2_decision/feature_store/extractors.py) 按 `atm_iv * 100 - settings.vrp_baseline_hv` 计算，而 [tactical_triad_logic.py](e:/US.market/Option_v3/shared/system/tactical_triad_logic.py) 会把 `0.15` 解释成 `15%`。这使同一配置在不同层被当成两种单位。

同时，`shared/models/microstructure.py` 仍保留 `200M/1000M` 老阈值注释，而 [agent_g.py](e:/US.market/Option_v3/shared/config/agent_g.py) 已改为 `20B/100B`。

## Decisions

1. `vol_risk_premium` 主口径统一为“百分比点差值”。
2. `shared/config/agent_g.py::vrp_baseline_hv` 继续允许 decimal 输入，但所有消费端必须先标准化为 `% points`。
3. Phase A 不新增运行时字段，仅修正现有字段语义和注释。
4. `GEX / zero_gamma / wall` 先通过注释、docstring、SOP 和服务层说明止血，不在本阶段引入新 metadata 字段。

## File-Level Plan

1. [extractors.py](e:/US.market/Option_v3/l2_decision/feature_store/extractors.py)
   - 收敛 `vol_risk_premium`
   - 更新 `net_gex_normalized` / `call_wall_distance` / `skew_25d_normalized` 的描述文字，明确 proxy 语义边界
2. [tactical_triad_logic.py](e:/US.market/Option_v3/shared/system/tactical_triad_logic.py)
   - 作为唯一 `VRP` 单位标准化源
3. [agent_g.py](e:/US.market/Option_v3/shared/config/agent_g.py)
   - 明确 `vrp_baseline_hv` 默认值的单位解释
   - 修正 GEX threshold 注释
4. [microstructure.py](e:/US.market/Option_v3/shared/models/microstructure.py)
   - 修正 `GexRegime` 注释
5. [enriched_snapshot.py](e:/US.market/Option_v3/l1_compute/output/enriched_snapshot.py) 与 [gamma_qual_analyzer.py](e:/US.market/Option_v3/l2_decision/agents/services/gamma_qual_analyzer.py)
   - 明确 wall/flip/zero-gamma 为 proxy semantics

## Test Plan

- 更新 [test_feature_store.py](e:/US.market/Option_v3/l2_decision/tests/test_feature_store.py)
  - 断言 `vol_risk_premium` 单位与 TacticalTriad 同口径
- 更新 [test_reactor_and_guards.py](e:/US.market/Option_v3/l2_decision/tests/test_reactor_and_guards.py)
  - 断言 `VRPVetoGuard` 使用统一后的 `% points` 解释
- 更新 [test_gamma_qual_analyzer.py](e:/US.market/Option_v3/l2_decision/tests/test_gamma_qual_analyzer.py)
  - 断言 `zero_gamma_level` 优先判定不变，同时文档/说明语义调整不破坏输出合同

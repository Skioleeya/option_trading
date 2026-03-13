## Context

审计文档已经明确：

- 标准 `VRP` 需要 risk-neutral vol 与 realized/physical vol 的差；
- 标准 `RR25` 需要 `IV_call(25Δ) - IV_put(25Δ)`；
- 当前主链只有 proxy 版本。

因此 Phase D 只做研究增强，不回写现网决策默认逻辑。

## Decisions

1. 新字段默认只进入 research / diagnostics / optional feature path。
2. `vol_risk_premium` 继续作为现网 feature，避免触发大范围策略回归。
3. `vrp_realized_based` 需要独立 realized vol 计算组件，优先放到 `shared/services/*` 中立边界。
4. inventory-aware gamma 仅预留命名，不伪造实现。

## File-Level Plan

1. 新增 [realized_volatility.py](e:/US.market/Option_v3/shared/services/realized_volatility.py)
2. 修改 [extractors.py](e:/US.market/Option_v3/l2_decision/feature_store/extractors.py)
   - 增加可选 `rr25_call_minus_put`
   - 增加可选 `vrp_realized_based`
3. 修改 [research_feature_store.py](e:/US.market/Option_v3/shared/services/research_feature_store.py)
   - 存储 dual-track skew/VRP 列

## Test Plan

- 新增建议测试：
  - [l2_decision/tests/test_feature_store.py](e:/US.market/Option_v3/l2_decision/tests/test_feature_store.py) 中覆盖 `rr25_call_minus_put`
  - [shared/tests/test_realized_volatility.py](e:/US.market/Option_v3/shared/tests/test_realized_volatility.py) 覆盖 realized vol 计算

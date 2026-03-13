## Context

[extractors.py](e:/US.market/Option_v3/l2_decision/feature_store/extractors.py) 已把 `skew_25d_normalized` 实现为 `(put - call) / atm_iv`，对应测试在 [test_feature_store.py](e:/US.market/Option_v3/l2_decision/tests/test_feature_store.py) 中已被固定。

同时 [streaming_aggregator.py](e:/US.market/Option_v3/l1_compute/aggregation/streaming_aggregator.py) 直接输出 `net_vanna`、`net_charm`，而审计确认它们只是链上 raw sensitivity 求和。

## Decisions

1. 保留现有 `skew_25d_normalized` 以避免打断 L2/L3/L4 现链路。
2. 新增 canonical `rr25_call_minus_put`，用于标准市场口径与研究导出。
3. 新增 canonical `net_vanna_raw_sum` / `net_charm_raw_sum`，并让旧字段作为兼容 alias。
4. 所有输出层都必须明确：
   - `skew_25d_normalized` = `put_minus_call_over_atm`
   - `rr25_call_minus_put` = 标准 risk reversal
   - `net_vanna_raw_sum` / `net_charm_raw_sum` ≠ inventory exposure

## File-Level Plan

1. [streaming_aggregator.py](e:/US.market/Option_v3/l1_compute/aggregation/streaming_aggregator.py)
   - dataclass 字段新增 canonical raw-sum 命名
2. [enriched_snapshot.py](e:/US.market/Option_v3/l1_compute/output/enriched_snapshot.py)
   - `to_dict()` 同时输出新旧字段
3. [reactor.py](e:/US.market/Option_v3/l1_compute/reactor.py)
   - 将 canonical raw-sum 字段透传到快照
4. [extractors.py](e:/US.market/Option_v3/l2_decision/feature_store/extractors.py)
   - 新增 `rr25_call_minus_put`
   - 为 `skew_25d_normalized` 补充精确描述
5. [gamma_qual_analyzer.py](e:/US.market/Option_v3/l2_decision/agents/services/gamma_qual_analyzer.py) 与 [greeks_extractor.py](e:/US.market/Option_v3/l2_decision/agents/services/greeks_extractor.py)
   - 切换到 canonical raw-sum 字段优先读取，同时保留旧字段回退
6. [research_feature_store.py](e:/US.market/Option_v3/shared/services/research_feature_store.py)
   - 研究导出中新增 canonical 列并保留旧列

## Test Plan

- 更新 [test_feature_store.py](e:/US.market/Option_v3/l2_decision/tests/test_feature_store.py)
  - 验证 `skew_25d_normalized`
  - 新增验证 `rr25_call_minus_put`
- 更新 [test_reactor.py](e:/US.market/Option_v3/l1_compute/tests/test_reactor.py)
  - 验证新旧 raw-sum 字段同时存在
- 更新 [test_gamma_qual_analyzer.py](e:/US.market/Option_v3/l2_decision/tests/test_gamma_qual_analyzer.py)
  - 验证优先读 canonical raw-sum，缺失时回退 legacy alias

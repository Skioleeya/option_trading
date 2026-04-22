## Why

审计文档指出：

- `skew_25d_normalized` 当前是 `(put_iv - call_iv) / atm_iv`，并非标准 `RR25`。
- `net_vanna` / `net_charm` 只是 raw Greek sum，不是 position-weighted exposure。

这属于合同可读性问题。若不显式收敛命名，下游会继续把工程字段误读为标准市场口径。

## What Changes

本子提案只处理 `RR25` 与 raw Greek sum 合同，不改 `FLOW_D/E/G`：

1. 为 25Δ skew 引入 canonical 字段：
   - 新增建议字段：`rr25_call_minus_put`
   - 保留现字段：`skew_25d_normalized`
   - 明确现字段语义：`put_minus_call_over_atm`
2. 为 raw Greek sum 引入更精确命名：
   - `net_vanna_raw_sum`
   - `net_charm_raw_sum`
   - 旧字段 `net_vanna` / `net_charm` 作为兼容 alias 保留一阶段
3. 在研究存储、L1 输出、L2 提取器和 gamma 分析服务中同步字段契约。

## Scope

- `l1_compute/aggregation/streaming_aggregator.py`
- `l1_compute/output/enriched_snapshot.py`
- `l1_compute/reactor.py`
- `l2_decision/feature_store/extractors.py`
- `l2_decision/agents/services/gamma_qual_analyzer.py`
- `l2_decision/agents/services/greeks_extractor.py`
- `shared/services/research_feature_store.py`
- `docs/SOP/L1_LOCAL_COMPUTATION.md`
- `docs/SOP/L2_DECISION_ANALYSIS.md`

## Parent

- `formula-semantic-contract-parent-governance`

# IV Metrics Map

## Scope

This file inventories the current repository metrics that are computed from IV or from IV-derived Greeks.

- `直接依赖IV = 是`: 公式直接使用 `IV/atm_iv/implied_volatility/historical_volatility`，或直接使用由 BSM + IV 计算出的 Greeks。
- `直接依赖IV = 否（间接）`: 指标本身不直接读 IV，但依赖上游已由 IV 驱动的 Greeks/GEX/wall/zero-gamma 结果。
- 当前仓库主口径仍为 `OI-based proxy`，不是 dealer inventory truth。

## Direct IV Dependencies

| 指标名 | 层级 | 是否直接依赖IV | 公式 / 来源文件 |
| --- | --- | --- | --- |
| `computed_iv` / `iv_used` / `atm_iv` | L1 | 是 | `L1ComputeReactor` 先做 `resolved_ivs`，再写入 `computed_iv`，并由最近 ATM 合约提取 `atm_iv`。来源: `l1_compute/reactor.py` |
| `delta` | L1 | 是 | BSM: `delta = N(d1)` call / `-N(-d1)` put。来源: `l1_compute/compute/gpu_greeks_kernel.py` |
| `gamma` | L1 | 是 | BSM: `gamma = exp(-qT) * n(d1) / (S * IV * sqrt(T))`。来源: `l1_compute/compute/gpu_greeks_kernel.py` |
| `vega` | L1 | 是 | BSM: `vega = S * exp(-qT) * n(d1) * sqrt(T) * 0.01`。来源: `l1_compute/compute/gpu_greeks_kernel.py` |
| `vanna` | L1 | 是 | BSM: `vanna = -exp(-qT) * n(d1) * d2 / IV * 0.01`。来源: `l1_compute/compute/gpu_greeks_kernel.py` |
| `charm` | L1 | 是 | BSM charm 由 `d1/d2/IV/T` 计算，代码中区分 call/put。来源: `l1_compute/compute/gpu_greeks_kernel.py` |
| `theta` | L1 | 是 | BSM theta 由 `d1/d2/IV/T` 计算，代码中区分 call/put。来源: `l1_compute/compute/gpu_greeks_kernel.py` |
| `gex_per_contract` / `call_gex` / `put_gex` | L1 | 是 | `gex = gamma * open_interest * contract_multiplier * spot^2 * 0.01 / 1_000_000`，其中 `gamma` 来自 IV。来源: `l1_compute/compute/gpu_greeks_kernel.py` |
| `total_call_gex` / `total_put_gex` / `net_gex` | L1 | 是 | 聚合 `call_gex/put_gex`，`net_gex = total_call_gex - total_put_gex`。来源: `l1_compute/aggregation/streaming_aggregator.py` |
| `net_vanna_raw_sum` / `net_charm_raw_sum`（`net_vanna` / `net_charm` 为兼容 alias） | L1 | 是 | 分别对链上 `vanna/charm` 求和；两者都来自 IV 驱动 Greeks，且当前只是 raw sum 不是仓位暴露。来源: `l1_compute/aggregation/streaming_aggregator.py` |
| `zero_gamma_level` | L1 | 是 | 在 spot 网格上重算 `gamma(S)` 与 `gex(S)`，`net_curve = sum(call_gex - put_gex)` 后做 zero-crossing 插值。来源: `l1_compute/aggregation/streaming_aggregator.py` |
| `iv_velocity` | L1 | 是 | `spot_roc = (spot_new - spot_old) / spot_old * 100`，`iv_roc = newest.iv - oldest.iv`，再做状态分类与 `confidence`。来源: `l1_compute/trackers/iv_velocity_tracker.py` |
| `mtf_consensus.timeframes.*.{state,relative_displacement,pressure_gradient,distance_to_vacuum,kinetic_level}` | L1 | 是 | `relative_displacement = (end_iv - start_iv) / start_iv`，`pressure_gradient = relative_displacement / dt`，其余几何量也直接由 ATM IV 帧计算。来源: `l1_compute/analysis/mtf_iv_engine.py` |
| `vanna_flow_result` / `svol_corr` / `svol_state` / `iv_roc` / `iv_acceleration` | L1 | 是 | 基于 spot 与 `atm_iv` 历史做 Pearson 相关、IV RoC、IV acceleration，再结合 `net_gex` 分类状态。来源: `l1_compute/trackers/vanna_flow_analyzer.py` |
| `iv_velocity_1m` | L2 | 是 | `velocity_per_min = ((iv - oldest_iv) / window_sec) * 60`，再按 `_REF_VELOCITY` 归一到 `[-1, 1]`。来源: `l2_decision/feature_store/extractors.py` |
| `svol_correlation_15m` | L2 | 是 | 用 15 分钟窗口内 `spot` 与 `atm_iv` 的 Pearson 相关系数，结果 clamp 到 `[-1, 1]`。来源: `l2_decision/feature_store/extractors.py` |
| `skew_25d_normalized` / `rr25_call_minus_put` / `skew_25d_valid` | L2 | 是 | 取最接近 `+0.25/-0.25` delta 的 call/put；legacy `skew_25d_normalized = (put_iv - call_iv) / atm_iv`，canonical `rr25_call_minus_put = call_iv - put_iv`；仅当双边 delta 都在容差内时有效。来源: `l2_decision/feature_store/extractors.py` |
| `mtf_consensus_score` | L2 | 是 | `0.5 * iv1m + 0.3 * iv5m + 0.2 * iv15m`，三个输入都来自 ATM IV velocity。来源: `l2_decision/feature_store/extractors.py` |
| `vol_risk_premium` | L2 | 是 | `vol_risk_premium = compute_vrp(atm_iv, settings.vrp_baseline_hv)`，输出 `% points`。来源: `l2_decision/feature_store/extractors.py`, `shared/system/tactical_triad_logic.py` |
| `realized_volatility_15m` / `vrp_realized_based` | L2 | 是 | `realized_volatility_15m` 基于 rolling spot log returns 年化得到 decimal RV；`vrp_realized_based` 先将 RV 显式转成 `%`，再计算 `ATM_IV(%) - realized_volatility(%)`，仅用于 research path。来源: `shared/services/realized_volatility.py`, `l2_decision/feature_store/extractors.py` |
| `iv_regime` | L2 | 是 | 用 `atm_iv`、`iv_velocity_1m` 与 `net_gex_normalized` 做 regime 分类；先对 `atm_iv` 做 5-tick smoothing。来源: `l2_decision/signals/iv_regime.py` |
| `guard_vrp_proxy_pct` / `VRPVetoGuard` | L2 | 是 | `guard_vrp_proxy_pct = ATM_IV(%) - realized_vol_proxy(%)`，其中 `realized_vol_proxy(%) = abs(vol_accel_ratio) * 10`；guard entry/exit 阈值统一按 `% points`，并兼容 legacy `0.15/0.13 -> 15.0/13.0`。来源: `shared/system/tactical_triad_logic.py`, `l2_decision/guards/rail_engine.py` |
| `vrp` / `vrp_state` | L3 | 是 | `compute_vrp(atm_iv, baseline_hv)`，即 `ATM_IV(%) - baseline_HV(%)`，再映射状态。来源: `shared/system/tactical_triad_logic.py`, `l3_assembly/assembly/ui_state_tracker.py` |
| `FLOW_E` | Shared / ActiveOptions | 是 | `delta_iv = implied_volatility - historical_volatility`；`flow_e = volume * 100 * abs(vanna) * abs(delta_iv) * direction`。来源: `shared/services/active_options/flow_engine_e.py` |
| `FLOW_G` | Shared / ActiveOptions | 是 | `iv_norm = implied_volatility / atm_iv`；`flow_g = delta_oi * iv_norm * turnover * type_sign`。来源: `shared/services/active_options/flow_engine_g.py` |

## Indirect IV Dependencies

| 指标名 | 层级 | 是否直接依赖IV | 公式 / 来源文件 |
| --- | --- | --- | --- |
| `call_wall` / `put_wall` | L1 | 否（间接） | 从各 strike 的 `call_gex/put_gex` 中选最大墙位；而 `call_gex/put_gex` 依赖 `gamma`，`gamma` 依赖 IV。来源: `l1_compute/aggregation/streaming_aggregator.py` |
| `flip_level_cumulative` / `flip_level` | L1 | 否（间接） | 按 strike 累加 `net_gex_by_strike`，取首次过零点；`net_gex` 来源于 IV 驱动的 gamma/GEX。来源: `l1_compute/aggregation/streaming_aggregator.py` |
| `gex_regime` | L1/L2 | 否（间接） | 基于 `net_gex` 的符号和幅度分类；`net_gex` 由 IV 驱动的 gamma 聚合而来。来源: `l1_compute/trackers/vanna_flow_analyzer.py`, `l2_decision/agents/services/gamma_qual_analyzer.py` |
| `gamma_flip` | L2 | 否（间接） | 优先按 `spot < zero_gamma_level` 判定，缺失时回退 `net_gex < 0`；`zero_gamma_level/net_gex` 都依赖 IV。来源: `l2_decision/agents/services/gamma_qual_analyzer.py` |
| `net_gex_normalized` | L2 | 否（间接） | `net_gex / 1000`，只是对 L1 `net_gex` 做 `$1B` 归一。来源: `l2_decision/feature_store/extractors.py` |
| `call_wall_distance` | L2 | 否（间接） | `(call_wall - spot) / spot`；其中 `call_wall` 来自 IV 驱动的 GEX 结构。来源: `l2_decision/feature_store/extractors.py` |
| `wall_migration_speed` | L2 | 否（间接） | 30 秒窗口内 `call_wall/put_wall` 相对速度之和，再归一化到 `[0, 1]`；墙位本身依赖 IV 驱动 GEX。来源: `l2_decision/feature_store/extractors.py` |
| `dealer_squeeze_alert` | L1/L2/L3 | 否（间接） | 来自微结构状态组合告警，底层依赖 wall / gex / vanna 相关结果；这些上游项均含 IV 依赖。来源: `shared/models/microstructure.py`, `l3_assembly/assembly/ui_state_tracker.py`, `shared/services/research_feature_store.py` |
| `counterfactual_vol_impact_bps` | L1/L3 | 否（间接） | 属于 wall-context 诊断项，依赖墙体/GEX/vanna 结构推导；不直接读 IV，但上游量由 IV 驱动。来源: `shared/models/microstructure.py`, `l3_assembly/assembly/ui_state_tracker.py` |
| `FLOW_D` | Shared / ActiveOptions | 否（间接） | `flow_d = volume * gamma * spot^2 * 100 * 0.01 * sign`；公式不直接读 IV，但 `gamma` 由 IV 计算。来源: `shared/services/active_options/flow_engine_d.py` |

## Notes

- `premium/standard` 当前通过 Tier2/Tier3 cache 进入 research diagnostics 汇总，但尚未进入 L1 live compute 主合同。
- `historical_volatility_decimal` 虽已在 L0 合同保真，本轮仍未进入主研究特征；是否采用它替代或补充本地 rolling RV 需单独决策。
- 若后续数据源具备 `aggressor_side/open_close/customer_type/dealer_type` 等标签，本表仍适用，但 `GEX/wall/flip` 的语义口径可能会从 `OI-based proxy` 升级为 inventory-based，需要单独改写文档。
- 本表只覆盖“当前仓库正在使用或向下游输出”的 IV 相关指标，不枚举测试专用字段或已废弃 legacy 命名。

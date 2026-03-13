# 期权论文公式与仓库实现一致性审计（2024-2026）

日期: 2026-03-12  
仓库: `E:\US.market\Option_v3`

## 检索方法

- 检索时间窗: 2024-01-01 至 2026-03-10。
- 检索方式: 使用 Google 风格 `site:` 查询词进行联网检索；在当前受限执行环境下，实际通过内置 web 搜索工具执行等价查询。
- 代表性检索词:
  - `site:ssrn.com/abstract option gamma exposure dealer hedging 2024`
  - `site:ssrn.com/abstract 0DTE gamma risk volatility propagation`
  - `site:sciencedirect.com option dealer hedging gamma exposure`
  - `site:sciencedirect.com variance risk premium option returns 2024`
  - `site:sciencedirect.com option flow turnover gamma impact`
  - `site:link.springer.com implied volatility skew 25 delta option`
- 优先级:
  - 期刊官网 / DOI / SSRN / NBER
  - arXiv 仅作补充，本次未作为核心依据
- 本地实现扫描范围:
  - `l1_compute/compute/gpu_greeks_kernel.py`
  - `l1_compute/aggregation/streaming_aggregator.py`
  - `l1_compute/trackers/iv_velocity_tracker.py`
  - `l1_compute/trackers/vanna_flow_analyzer.py`
  - `l1_compute/analysis/mtf_iv_engine.py`
  - `l1_compute/trackers/wall_migration_tracker.py`
  - `l2_decision/feature_store/extractors.py`
  - `l2_decision/signals/iv_regime.py`
  - `l2_decision/guards/rail_engine.py`
  - `l2_decision/agents/services/gamma_qual_analyzer.py`
  - `shared/services/active_options/flow_engine_d.py`
  - `shared/services/active_options/flow_engine_e.py`
  - `shared/services/active_options/flow_engine_g.py`
  - `shared/system/tactical_triad_logic.py`
  - `shared/config/agent_g.py`
  - `shared/config/market_structure.py`
  - `shared/models/microstructure.py`

## 纳入标准与排除标准

### 纳入标准

- 2024-2026 的期权研究论文或 working paper。
- 论文主题与下列至少一项直接相关:
  - Greeks / gamma / dealer hedging
  - implied volatility surface / skew / risk reversal
  - volatility risk premium
  - option order flow / open interest / demand pressure
  - 0DTE / option market microstructure
- 能为仓库指标提供至少一种下列信息:
  - 公式
  - 单位定义
  - 符号方向
  - 分类规则
  - 明确的“不提供固定阈值”

### 排除标准

- 博客、媒体、培训站点、交易员评论。
- 仅复述旧文献而无新增定义的二手综述。
- 与仓库指标无直接映射关系的纯理论数学推导。

## 论文清单

| 论文 | 年份 | 来源 | 状态 | 相关主题 |
| --- | --- | --- | --- | --- |
| [0DTE Index Options and Market Volatility: How Large is Their Impact?](https://ssrn.com/abstract=5113405) | 2025 | SSRN | working paper / not peer-reviewed | 0DTE, OMM gamma, hedging impact |
| [The role of intermediaries in derivatives markets: Evidence from VIX options](https://doi.org/10.1016/j.jempfin.2024.101492) | 2024 | Journal of Empirical Finance | peer-reviewed | option demand pressure, cross-market spillover |
| [Volatility risk premium, good volatility and bad volatility: Evidence from SSE 50 ETF options](https://doi.org/10.1016/j.najef.2024.102206) | 2024 | North American Journal of Economics and Finance | peer-reviewed | VRP, realized volatility decomposition |
| [Forecasting implied volatilities of currency options with machine learning techniques and econometrics models](https://doi.org/10.1007/s41060-024-00528-7) | 2025 | International Journal of Data Science and Analytics | peer-reviewed | IV surface, risk reversal, 25-delta skew |
| [Predicting Short-Term Stock Returns with Weekly Options Indicators: Comparative Study of Key Market Movers, SPY, and S&P 500 Index](https://doi.org/10.1142/S2010139225500041) | 2025 | Quarterly Journal of Finance | peer-reviewed | open interest, volume, weekly options indicators |
| [The stock market impact of volatility hedging: Evidence from end-of-day trading by VIX ETPs](https://doi.org/10.1016/j.jbankfin.2025.107556) | 2025 | Journal of Banking & Finance | peer-reviewed | volatility hedging, net gamma position, end-of-day impact |
| [Retail option traders and the implied volatility surface](https://doi.org/10.1016/j.jfineco.2026.104238) | 2026 | Journal of Financial Economics | peer-reviewed | IV term structure, moneyness curve, call-put spread |
| [Decomposing informed trading in equity options](https://doi.org/10.1016/j.jeconom.2025.106131) | 2026 | Journal of Econometrics | peer-reviewed | option flow, delta/vega decomposition, straddles |

## 仓库指标审计总表

### L1

| 指标名 | 层级 | 仓库公式/阈值 | 论文公式/阈值 | 来源论文 | 是否一致 | 偏差说明 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `delta` | L1 | `e^{-qT}N(d1)` call, `-e^{-qT}N(-d1)` put；`l1_compute/compute/gpu_greeks_kernel.py` | 近年论文继续沿用标准 BSM / Garman-Kohlhagen delta 口径 | Olsen et al. 2025 | 是 | 无固定阈值问题 | 与论文标准公式一致；论文未提供固定通用阈值 |
| `gamma` | L1 | `e^{-qT}n(d1)/(Sσ√T)`；`l1_compute/compute/gpu_greeks_kernel.py` | 标准 gamma 定义 | Olsen et al. 2025 | 是 | 无 | 与论文标准公式一致；论文未提供固定通用阈值 |
| `vega` | L1 | `S e^{-qT} n(d1) √T * 0.01`，按 1 vol point；`l1_compute/compute/gpu_greeks_kernel.py` | 标准 vega 定义，常按 1 vol point 或 1.0 vol 单位展示 | Olsen et al. 2025 | 部分一致 | 仓库明确按 1 vol point 缩放；论文通常不强制统一展示单位 | 与论文标准公式基本一致；论文未提供固定通用阈值 |
| `vanna` | L1 | `-e^{-qT}n(d1)d2/σ * 0.01`；`l1_compute/compute/gpu_greeks_kernel.py` | 近年论文讨论 vanna 风险时沿用标准 sensitivity 定义 | Decomposing informed trading in equity options 2026（以 delta/vega 敏感度分解为主） | 部分一致 | 单合约 Greek 一致，但论文更关注仓位加权后的交易/库存效应 | 与论文标准公式基本一致；论文未提供固定通用阈值 |
| `charm` | L1 | BSM charm，call/put 分式后再 `/365`；`l1_compute/compute/gpu_greeks_kernel.py` | 近年纳入论文未给统一 charm 阈值或替代公式 | 无统一 2024-2026 固定定义 | 部分一致 | 公式属于标准 Greeks；但纳入论文基本不提供 charm 分类阈值 | 与论文标准公式基本一致；论文未提供固定通用阈值 |
| `theta` | L1 | 标准 BSM theta，`/365` 转日度；`l1_compute/compute/gpu_greeks_kernel.py` | 标准 theta 定义 | Olsen et al. 2025 | 是 | 无 | 与论文标准公式一致；论文未提供固定通用阈值 |
| `gex_per_contract` | L1 | `gamma * OI * multiplier * spot^2 * 0.01 / 1e6`，单位 MMUSD；`l1_compute/compute/gpu_greeks_kernel.py` | 近年论文更常用真实 MM/OMM gamma 或净仓位 gamma；例如 `NGP = Σ gamma_i * position_i * multiplier_i` | Vasquez et al. 2025; Bangsgaard & Kokholm 2025 | 部分一致 | 仓库用 `open_interest` 替代真实做市商持仓，属于 OI-based proxy | 仓库工程派生，不是标准学术定义 |
| `call_gex` | L1 | `np.where(is_call, gex_raw, 0)`，非负幅度；`l1_compute/compute/gpu_greeks_kernel.py` | 论文多从真实净仓位出发，不强制“call gross non-negative”展示 | Vasquez et al. 2025 | 部分一致 | 仓库先做 gross side buckets，再由 `net_gex = call - put` 得净值 | 仓库工程派生，不是标准学术定义 |
| `put_gex` | L1 | `np.where(~is_call, gex_raw, 0)`，非负幅度；`l1_compute/compute/gpu_greeks_kernel.py` | 同上 | Vasquez et al. 2025 | 部分一致 | 与真实 dealer short/long sign 不是一回事 | 仓库工程派生，不是标准学术定义 |
| `net_gex` | L1 | `sum(call_gex) - sum(put_gex)`；`l1_compute/aggregation/streaming_aggregator.py` | 论文讨论的净 gamma 常基于真实库存/净需求，不是简单 `OI call minus OI put` | Vasquez et al. 2025; Bangsgaard & Kokholm 2025 | 部分一致 | 方向语义可类比“long gamma vs short gamma”，但不是 dealer truth | 仓库工程派生，不是标准学术定义 |
| `call_wall` | L1 | 选 `call_gex` 最大且优先 `strike >= spot`；`l1_compute/aggregation/streaming_aggregator.py` | 纳入论文未给统一 `call wall` 学术定义 | 未检得 2024-2026 统一正式定义 | 否 | 这是交易实务/UI 术语，不是标准论文指标 | 仓库工程派生，不是标准学术定义 |
| `put_wall` | L1 | 选 `put_gex` 最大且优先 `strike <= spot`；`l1_compute/aggregation/streaming_aggregator.py` | 纳入论文未给统一 `put wall` 学术定义 | 未检得 2024-2026 统一正式定义 | 否 | 同上 | 仓库工程派生，不是标准学术定义 |
| `flip_level_cumulative` | L1 | 排序后累计 `net_gex_by_strike` 首次过零；`l1_compute/aggregation/streaming_aggregator.py` | 论文讨论 zero-gamma 时更常重算 `net_gamma(S)`；很少用 cumulative depth crossing 当正式定义 | Vasquez et al. 2025（讨论 OMM gamma 符号） | 否 | 这是 depth-profile 语义，不等同 zero-gamma | 仓库工程派生，不是标准学术定义 |
| `zero_gamma_level` | L1 | 在 spot 网格上重算 `net_gex(S)`，取离现货最近的零点；`l1_compute/aggregation/streaming_aggregator.py` | 与 dealer gamma sign / zero-crossing 概念方向一致，但论文通常用真实 OMM position gamma | Vasquez et al. 2025; Bangsgaard & Kokholm 2025 | 部分一致 | 计算思想一致，输入仍是 OI proxy 而非真实 dealer 仓位 | 与论文概念部分一致，但仓库仍是 OI-based proxy |
| `net_vanna` | L1 | 直接对全链 `vanna` 求和；`l1_compute/aggregation/streaming_aggregator.py` | 近年论文谈 vanna 影响时通常关注仓位加权或流量加权 vanna 暴露 | Retail option traders 2026；Decomposing informed trading 2026 | 否 | 仓库未乘 `OI/volume/notional`，不是标准 exposure 口径 | 仓库工程派生，不是标准学术定义 |
| `net_charm` | L1 | 直接对全链 `charm` 求和；`l1_compute/aggregation/streaming_aggregator.py` | 近年纳入论文未提供统一 charm exposure 公式/阈值 | 未检得统一 2024-2026 口径 | 否 | 同样缺少仓位/名义权重 | 仓库工程派生，不是标准学术定义 |
| `iv_velocity` | L1 | 120s 窗口；`spot_roc` 与 `iv_roc` 分类；阈值 `0.03%` spot、`2pp` IV；`l1_compute/trackers/iv_velocity_tracker.py` | 论文讨论 IV surface / moneyness curve / term structure 变化，但未给这种状态机阈值 | Eaton et al. 2026; Olsen et al. 2025 | 否 | 状态命名与阈值均为在线工程规则 | 仓库工程派生，不是标准学术定义；论文未提供固定通用阈值 |
| `mtf_consensus` | L1 | 几何帧 `relative_displacement / pressure_gradient / kinetic_level`；阈值 `1m=0.003,5m=0.0045,15m=0.006`；`l1_compute/analysis/mtf_iv_engine.py` | 纳入论文未给统一 multi-timeframe 几何状态机 | 未检得统一 2024-2026 口径 | 否 | 完全是前台/决策工程结构 | 仓库工程派生，不是标准学术定义；论文未提供固定通用阈值 |
| `vanna_flow_result` | L1 | Pearson `corr(spot, atm_iv)` + flip/acceleration/GEX state；阈值 `danger>0.8`、`grind<-0.2`、`flip Δcorr>0.6/2min`；`l1_compute/trackers/vanna_flow_analyzer.py` | 论文支持“spot-vol correlation / demand pressure影响 smile”，但未给统一阈值 | Eaton et al. 2026; Olsen et al. 2025 | 部分一致 | 相关性概念有学术对应，但状态机阈值为工程经验 | 仓库工程派生，不是标准学术定义；论文未提供固定通用阈值 |
| `svol_corr` | L1 | 直接取 vanna analyzer 的 spot-vol Pearson correlation；`shared/system/tactical_triad_logic.py` | spot-vol / skewness 关系在近期论文中常见 | Eaton et al. 2026; Olsen et al. 2025 | 部分一致 | 统计量本身标准，但窗口与阈值非统一文献标准 | 与论文统计量概念一致；论文未提供固定通用阈值 |
| `svol_state` | L1 | `DANGER_ZONE / GRIND_STABLE / VANNA_FLIP / NORMAL`；`shared/system/tactical_triad_logic.py` | 近期论文未给统一状态标签 | 无统一正式定义 | 否 | 展示/决策态，不是论文态 | 仓库工程派生，不是标准学术定义 |

### L2

| 指标名 | 层级 | 仓库公式/阈值 | 论文公式/阈值 | 来源论文 | 是否一致 | 偏差说明 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `net_gex_normalized` | L2 | `clip(net_gex / 1000, -1, 1)`；`l2_decision/feature_store/extractors.py` | 论文未给统一 `$1B` 归一口径 | Vasquez et al. 2025 | 否 | 在线信号归一化，不是学术定义 | 仓库工程派生，不是标准学术定义 |
| `call_wall_distance` | L2 | `(call_wall - spot)/spot`；`l2_decision/feature_store/extractors.py` | 论文未给统一 wall-distance 指标 | 未检得统一正式定义 | 否 | 来源于交易实务墙位概念 | 仓库工程派生，不是标准学术定义 |
| `wall_migration_speed` | L2 | 30s 内 call/put wall 相对速度之和，再按 `0.001` 归一；`l2_decision/feature_store/extractors.py` | 论文未给统一 wall migration speed 公式 | 未检得统一正式定义 | 否 | 纯工程时间序列特征 | 仓库工程派生，不是标准学术定义 |
| `iv_velocity_1m` | L2 | `((iv-oldest_iv)/window)*60 / 0.02` clamp 到 `[-1,1]`；`l2_decision/feature_store/extractors.py` | 论文未给统一“1m IV velocity normalized by 0.02”口径 | Olsen et al. 2025 | 否 | 标度和截断完全工程化 | 仓库工程派生，不是标准学术定义 |
| `svol_correlation_15m` | L2 | 15 分钟 Pearson 相关；`l2_decision/feature_store/extractors.py` | Pearson 相关本身标准；无统一固定窗口阈值 | Eaton et al. 2026 | 部分一致 | 统计量一致，窗口是工程选择 | 与论文统计量概念一致；论文未提供固定通用阈值 |
| `skew_25d_normalized` | L2 | 取最接近 `+0.25/-0.25` delta 的 call/put，`(put_iv - call_iv)/atm_iv`；`l2_decision/feature_store/extractors.py` | 近期论文沿用 25-delta risk reversal 衡量 skew，通常是 `IV_call(25Δ) - IV_put(25Δ)` 或等价负值表述 | Olsen et al. 2025 | 部分一致 | `25Δ` 选腿一致，但仓库做了 sign 翻转并再除以 `atm_iv`；这不是标准 RR25 报价 | 与论文概念部分一致，但符号与归一化不一致 |
| `skew_25d_valid` | L2 | 双边 delta 都在 `±0.10` 容差内记 1，否则 0；`l2_decision/feature_store/extractors.py` | 论文未给统一容差 flag 指标 | Olsen et al. 2025 | 否 | 这是数据质量守卫，不是论文指标 | 仓库工程派生，不是标准学术定义；论文未提供固定通用阈值 |
| `mtf_consensus_score` | L2 | `0.5*iv1m + 0.3*iv5m + 0.2*iv15m`；`l2_decision/feature_store/extractors.py` | 论文未给统一跨周期权重 | 无统一正式定义 | 否 | 完全工程加权 | 仓库工程派生，不是标准学术定义 |
| `vol_risk_premium` | L2 | `atm_iv*100 - settings.vrp_baseline_hv`；`l2_decision/feature_store/extractors.py` | 论文中的 VRP 是风险中性波动/方差与物理世界 realized volatility 之差，而非固定常数基线 | Li et al. 2024 | 否 | 仓库用固定 baseline HV proxy；且当前默认 `0.15` 与 L3 的 15% 解释存在单位不一致 | 仓库工程派生，不是标准学术定义 |
| `iv_regime` | L2 | `iv_low=0.12`, `iv_high=0.25`, `velocity_weight=0.3`, `gex_amp=0.15`, `hysteresis=3`；`l2_decision/signals/iv_regime.py` | 论文讨论高低波动状态，但未给统一这些阈值/权重 | Li et al. 2024; Eaton et al. 2026 | 否 | 分类器是工程决策层产物 | 仓库工程派生，不是标准学术定义；论文未提供固定通用阈值 |
| `gamma_flip` | L2 | 优先 `spot < zero_gamma_level`，否则 `net_gex < 0`；`l2_decision/agents/services/gamma_qual_analyzer.py` | 与“负 gamma regime”概念方向一致 | Vasquez et al. 2025; Bangsgaard & Kokholm 2025 | 部分一致 | 概念对，但依赖上游 OI proxy | 与论文概念部分一致，但仓库仍是 OI-based proxy |
| `VRPVetoGuard` | L2 | `vrp = atm_iv - |vol_accel_ratio|*0.10`；entry `0.15`，exit `0.13`，hold `3/2`；`l2_decision/guards/rail_engine.py` | 纳入论文未给统一交易 veto 阈值 | Li et al. 2024 | 否 | realized vol 用 `vol_accel_ratio` 代理，阈值完全工程化 | 仓库工程派生，不是标准学术定义；论文未提供固定通用阈值 |

### Shared / ActiveOptions

| 指标名 | 层级 | 仓库公式/阈值 | 论文公式/阈值 | 来源论文 | 是否一致 | 偏差说明 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FLOW_D` | Shared / ActiveOptions | `volume * gamma * spot^2 * 100 * 0.01 * sign(type)`；`shared/services/active_options/flow_engine_d.py` | 近年论文支持 gamma hedging 方向影响，但未给这一公开数据合成公式 | Vasquez et al. 2025; Bangsgaard & Kokholm 2025 | 否 | 用 `volume` 代替真实 dealer inventory / signed trade flow | 仓库工程派生，不是标准学术定义 |
| `FLOW_E` | Shared / ActiveOptions | `volume * 100 * |vanna| * |IV-HV| * direction`；`shared/services/active_options/flow_engine_e.py` | 纳入论文未给统一 `vanna x ΔIV x volume` flow 公式 | Eaton et al. 2026; Retail option traders 2026 | 否 | 更像研究启发式 composite，不是论文标准式 | 仓库工程派生，不是标准学术定义 |
| `FLOW_G` | Shared / ActiveOptions | `ΔOI * (IV/ATM_IV) * turnover * sign(type)`；`shared/services/active_options/flow_engine_g.py` | 近期论文使用 OI/volume/demand 预测，但未给这一 exact composite formula | Saba et al. 2025; Jacobs & Mai 2024 | 否 | 方向上借鉴 OI 与 demand pressure，公式本身非标准学术定义 | 仓库工程派生，不是标准学术定义 |

## 关键概念差异说明

### 1. `GEX`

- 学术近似:
  - 2024-2026 纳入论文更常研究真实做市商或 OMM 的净 gamma、净需求、库存冲击，核心对象是 `position/inventory/demand pressure`。
  - 例如 `The stock market impact of volatility hedging...` 使用标准化的 `D_t^{ETP}` 作为机械需求冲击；`0DTE Index Options...` 直接估计 OMM aggregate gamma。
- 仓库实现:
  - `gex_per_contract = gamma * OI * multiplier * S^2 * 0.01 / 1e6`
  - `net_gex = call_gex - put_gex`
- 结论:
  - 仓库不是 dealer truth。
  - 这是 `OI-based proxy GEX`，适合作为工程结构信号，不应写成“论文支持的真实 dealer gamma”。

### 2. `zero_gamma_level`

- 学术/实务共识:
  - 更接近“让净 gamma 过零的现货位置”。
  - 近期论文讨论的是 gamma sign / hedging impact，而不是统一零点算法模板。
- 仓库实现:
  - 在 `spot` 网格上重算 `gamma(S)` 与 `gex(S)`，再对 `net_curve(S)` 做过零插值。
- 结论:
  - 算法思想与实务 zero-gamma 概念一致。
  - 但因为输入仍是 `OI-based proxy`，输出必须表述为 `OI-based zero-gamma proxy`。

### 3. `flip_level_cumulative`

- 论文现状:
  - 本轮纳入论文没有把“按 strike 深度累加后首个过零点”当作统一学术定义。
- 仓库实现:
  - 这是深度分布图语义，用于描述按 strike 累计净 GEX 的结构翻转。
- 结论:
  - 不能把 `flip_level_cumulative` 当成 `zero_gamma_level` 的学术同义词。
  - 它更像前台/结构分析指标。

### 4. `call_wall` / `put_wall`

- 论文现状:
  - 2024-2026 纳入论文没有统一的 `call wall` / `put wall` 正式定义。
  - 论文讨论的是 demand pressure、pinning、high OI strikes、dealer hedging，不是统一名词表。
- 仓库实现:
  - `call_wall` = call GEX 最大 strike；`put_wall` = put GEX 最大 strike，并加上 spot 侧优先规则。
- 结论:
  - 这是交易实务术语。
  - 报告和 UI 可以保留，但必须标注为 `trading-practice wall proxy`。

## 高优先级偏差项

1. `vol_risk_premium` 的基线单位在 L2 和 L3 不一致。
   - L2: `l2_decision/feature_store/extractors.py` 使用 `atm_iv * 100 - settings.vrp_baseline_hv`
   - 配置: `shared/config/agent_g.py` 默认 `vrp_baseline_hv = 0.15`
   - L3: `shared/system/tactical_triad_logic.py` 会把 `0.15` 解释成 `15.0%`
   - 结果: L2 特征层当前更像 `18 - 0.15`，L3 展示层更像 `18 - 15`

2. `GEX` regime 注释阈值和实际配置阈值不一致。
   - 注释/模型文档: `shared/models/microstructure.py` 仍写 `200M/1000M`
   - 实际配置: `shared/config/agent_g.py` 是 `20B/100B`，即 `20000/100000 MMUSD`
   - 结果: 容易误把当前 regime 门槛理解低了两个数量级

3. `skew_25d_normalized` 的符号与标准 `RR25` 报价不一致。
   - 论文/市场习惯常写 `RR25 = IV_call(25Δ) - IV_put(25Δ)`
   - 仓库写 `(put_iv - call_iv) / atm_iv`
   - 结果: 同一市场状态下，仓库数值方向与标准 RR25 相反，且多了 ATM 归一化

4. `net_vanna` / `net_charm` 不是标准“暴露”口径。
   - 仓库只是链上 raw Greeks 求和
   - 未乘 `OI`、`multiplier`、`notional`
   - 容易被误读为学术上的 aggregate exposure

5. `call_wall` / `put_wall` / `flip_level_cumulative` 没有 2024-2026 统一论文定义。
   - 只能写成交易工程 proxy
   - 不应声称“有论文统一标准”

6. `FLOW_D/E/G` 没有检得 2024-2026 peer-reviewed 的 exact 同式支持。
   - 只能写为启发式研究特征
   - 不能写成标准期权微结构公式

## 建议修正项

1. 在所有 GEX 相关输出上明确补标签: `OI-based proxy`, `not dealer inventory truth`。
2. 统一 `vol_risk_premium` 的 baseline 单位，至少让 L2 与 L3 同时按 `%` 或同时按 `decimal`。
3. 在 `skew_25d_normalized` 文档中显式注明:
   - 使用 `25Δ` 选腿
   - 当前符号是 `put - call`
   - 当前又额外除以 `atm_iv`
4. 给 `net_vanna` / `net_charm` 改名或补注释，例如:
   - `net_vanna_raw_sum`
   - `net_charm_raw_sum`
5. 在 `shared/models/microstructure.py` 和相关文档里同步 GEX regime 阈值口径，消除 `200M/1000M` 与 `20B/100B` 混写。
6. 给 `FLOW_D/E/G` 增加 provenance 注释:
   - `research heuristic`
   - `public-data proxy`
   - `not standard academic formula`

## 不建议修正项

1. 不建议为了“贴论文”删除 `call_wall` / `put_wall` / `flip_level_cumulative`。
   - 它们对前台结构表达仍有价值
   - 只需要改表述，不需要删掉

2. 不建议把 `zero_gamma_level` 改成论文式真实 OMM gamma，除非数据源新增真实 dealer inventory。
   - 当前数据能力不支持

3. 不建议把 `iv_velocity` / `mtf_consensus` / `VRPVetoGuard` 强行包装成学术指标。
   - 它们本质上是在线决策 heuristics

## 数据能力边界说明

- 当前主链路没有逐笔 `dealer/customer/open_close/aggressor_side` 标签。
- 当前没有真实做市商库存，只能观测公开 `open_interest`、`volume`、`turnover` 等。
- 因此以下指标天然只能是 proxy:
  - `gex_per_contract`
  - `call_gex`
  - `put_gex`
  - `net_gex`
  - `zero_gamma_level`
  - `call_wall`
  - `put_wall`
  - `FLOW_D`
  - `FLOW_E`
  - `FLOW_G`
- 论文若基于 proprietary dealer/OMM positions，其结论只能用于方向性对照，不能直接视为仓库公式的逐项验证。

## 总结结论

1. 仓库与论文最一致的部分是 L1 的基础 Greeks 公式: `delta/gamma/vega/theta/vanna/charm` 仍是标准 BSM 系。
2. `zero_gamma_level` 的计算思想与学术/实务“净 gamma 过零点”概念相近，但输入仍是 `OI-based proxy`，不是 dealer truth。
3. `GEX`、`call_wall`、`put_wall`、`flip_level_cumulative` 都不能写成统一学术标准定义；其中只有 `zero_gamma_level` 具备较强概念可比性。
4. `net_vanna` 和 `net_charm` 当前只是 raw Greek sum，不是标准仓位暴露。
5. `skew_25d_normalized` 只在“25Δ 选腿”上与近期论文/市场惯例一致；其符号和 ATM 归一化与标准 RR25 不同。
6. `vol_risk_premium` 不是论文中的标准 VRP，只是固定 baseline-HV proxy；且 L2/L3 当前存在单位口径不一致。
7. `iv_velocity`、`mtf_consensus`、`vanna_flow_result`、`iv_regime`、`VRPVetoGuard` 属于在线工程状态机，论文未提供固定通用阈值。
8. `FLOW_D/E/G` 是研究启发式工程合成，不是 2024-2026 论文中的统一标准公式。
9. 论文能支持的是“方向关系”和“概念边界”，不能支持仓库多数阈值；多数阈值只能标注为样本内/工程校准。
10. 若未来要宣称“与论文一致”，建议仅对基础 Greeks 公式和 zero-gamma 概念层做此表述，其他字段统一改成 `proxy / heuristic / engineering-derived`。

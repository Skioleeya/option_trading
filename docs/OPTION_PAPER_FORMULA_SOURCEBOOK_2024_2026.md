# 期权论文公式源手册（2024-2026）

日期: 2026-03-12  
仓库: `E:\US.market\Option_v3`

## 1. 0DTE Index Options and Market Volatility: How Large is Their Impact?

- 标题: 0DTE Index Options and Market Volatility: How Large is Their Impact?
- 作者: Aurelio Vasquez, Diego Amaya, Neil D. Pearson, Pedro Angel Garcia-Ares
- 年份: 2025
- 期刊/SSRN/arXiv: SSRN working paper
- 链接: https://ssrn.com/abstract=5113405
- 研究主题: 0DTE、OMM gamma、hedge rebalancing 与指数波动
- 原论文公式:
  - 摘要可见的核心定义不是公开 OI 公式，而是“用 proprietary trade data 估计 OMM aggregate position and gamma”，再在“OMM gamma impacts volatility / does not impact volatility”的反事实模型之间比较。
  - 也就是说，论文的 gamma 是真实 OMM 持仓层面的 gamma，不是 `open_interest` 替身。
- 原论文阈值/分类规则:
  - 论文以 OMM gamma 的正负及其对波动的边际影响为核心。
  - 论文未提供固定通用阈值。
- 适用前提:
  - 需要 proprietary 逐笔交易与做市商聚合头寸。
  - 适用于 SPX 0DTE 指数期权研究，不等于任意公开链数据都可复现。
- 对应仓库指标:
  - `gex_per_contract`
  - `call_gex`
  - `put_gex`
  - `net_gex`
  - `zero_gamma_level`
  - `gamma_flip`
- 解释性摘要:
  - 这篇论文最重要的启发是: 学术上更关心真实 OMM gamma 及其 hedging 后果，而不是单纯的 OI 累乘式。
  - 因此仓库 GEX 可用于方向研究，但必须标明 `OI-based proxy`。

## 2. The role of intermediaries in derivatives markets: Evidence from VIX options

- 标题: The role of intermediaries in derivatives markets: Evidence from VIX options
- 作者: Kris Jacobs, Anh Thu Mai
- 年份: 2024
- 期刊/SSRN/arXiv: Journal of Empirical Finance
- 链接: https://doi.org/10.1016/j.jempfin.2024.101492
- 研究主题: intermediary demand pressure、VIX/SPX option markets spillover
- 原论文公式:
  - 论文核心是 daily aggregate net demand variables。
  - 摘要明确写到作者“construct a measure of daily aggregate net demand for VIX call and put options”，并用其解释 implied volatility 变化。
- 原论文阈值/分类规则:
  - 论文未给固定通用阈值。
  - 更关注 demand shock 的动态 spillover，而非统一状态机阈值。
- 适用前提:
  - 需要 CBOE open-close 数据或等价的订单方向聚合数据。
  - 适用于 demand pressure，而不是公开 OI 的静态替代。
- 对应仓库指标:
  - `FLOW_G`
  - `FLOW_D`
  - `call_wall`
  - `put_wall`
  - `iv_regime`
- 解释性摘要:
  - 论文支持“net demand pressure 会影响 option prices / IV / 跨市场 spillover”这一方向。
  - 但它不支持把 `open_interest`、`turnover`、`volume` 随意拼成统一标准公式。

## 3. Volatility risk premium, good volatility and bad volatility: Evidence from SSE 50 ETF options

- 标题: Volatility risk premium, good volatility and bad volatility: Evidence from SSE 50 ETF options
- 作者: Zhe Li, Jiashuang Shen, Weilin Xiao
- 年份: 2024
- 期刊/SSRN/arXiv: North American Journal of Economics and Finance
- 链接: https://doi.org/10.1016/j.najef.2024.102206
- 研究主题: VRP、realized volatility、good/bad volatility
- 原论文公式:
  - 论文明确定义:
    - `RV_t = sqrt(sum_i r_{t,i}^2)`
    - good / bad volatility 来自日内正负收益平方和的拆分
    - VRP 是“risk-neutral measure volatility”和“realistic / physical measure volatility”的差
- 原论文阈值/分类规则:
  - 论文按 option type、market condition、moneyness 分组比较。
  - 论文未提供固定通用阈值。
- 适用前提:
  - 需要高频 realized volatility 或可替代的 realized variance。
  - 需要能区分风险中性波动与物理世界波动。
- 对应仓库指标:
  - `vol_risk_premium`
  - `VRPVetoGuard`
  - `iv_regime`
- 解释性摘要:
  - 论文支持“VRP 不是一个固定常数减法”，而是风险中性波动与 realized/physical volatility 的差。
  - 因此仓库 `atm_iv*100 - baseline_hv` 只能是 proxy，不能写成标准 VRP。

## 4. Forecasting implied volatilities of currency options with machine learning techniques and econometrics models

- 标题: Forecasting implied volatilities of currency options with machine learning techniques and econometrics models
- 作者: Asbjørn Olsen, Gard Djupskås, Petter Eilif de Lange, Morten Risstad
- 年份: 2025
- 期刊/SSRN/arXiv: International Journal of Data Science and Analytics
- 链接: https://doi.org/10.1007/s41060-024-00528-7
- 研究主题: implied volatility surface、moneyness、25-delta risk reversal
- 原论文公式:
  - 论文样本直接使用不同 delta bucket 的 call/put IV。
  - 文中明确指出最常见的 skew 度量是 `25-delta risk reversal`。
  - 文义上对应:
    - `RR25 = IV_call(25Δ) - IV_put(25Δ)`
    - 如果 OTM put IV 更高，则 RR25 为负，反映负 skew。
- 原论文阈值/分类规则:
  - 文中未给固定阈值。
  - 使用 delta bucket: `5, 10, 18, 25, 35, 50(ATM put)`。
- 适用前提:
  - 需要有足够密度的 smile surface 和 delta bucket。
  - 风险反转是 smile skewness 的市场惯例度量。
- 对应仓库指标:
  - `skew_25d_normalized`
  - `skew_25d_valid`
  - `iv_velocity`
  - `iv_velocity_1m`
- 解释性摘要:
  - 这篇论文是本次审计中最直接支持 `25Δ` 选腿的来源。
  - 但它不支持仓库当前的 `(put_iv - call_iv)/atm_iv` 归一方式，也不支持 `±0.10` 容差阈值。

## 5. Predicting Short-Term Stock Returns with Weekly Options Indicators: Comparative Study of Key Market Movers, SPY, and S&P 500 Index

- 标题: Predicting Short-Term Stock Returns with Weekly Options Indicators: Comparative Study of Key Market Movers, SPY, and S&P 500 Index
- 作者: Zannatus Saba, Rafiqul Bhuyan, Coşkun Çetin
- 年份: 2025
- 期刊/SSRN/arXiv: Quarterly Journal of Finance
- 链接: https://doi.org/10.1142/S2010139225500041
- 研究主题: weekly options indicators、open interest、volume、short-term returns
- 原论文公式:
  - 论文不是单一 closed-form factor，而是把 lagged call/put OI 与 call/put volume 当作 predictors。
  - 重点是 `lagged open interest call/put`、`call/put volume` 的统计显著性。
- 原论文阈值/分类规则:
  - 论文未提供固定通用阈值。
  - 使用 weekly option maturity 与回归/GARCH 框架做预测比较。
- 适用前提:
  - 适合公开 OI 与 volume 丰富、按周到期结构明显的市场。
- 对应仓库指标:
  - `FLOW_G`
  - `FLOW_D`
  - `call_wall`
  - `put_wall`
- 解释性摘要:
  - 该文支持“公开 OI / volume 本身有信息含量”。
  - 但它不支持把这些量拼成仓库当前 `FLOW_G` 或 `call_wall/put_wall` 的 exact academic formula。

## 6. The stock market impact of volatility hedging: Evidence from end-of-day trading by VIX ETPs

- 标题: The stock market impact of volatility hedging: Evidence from end-of-day trading by VIX ETPs
- 作者: Christine Bangsgaard, Thomas Kokholm
- 年份: 2025
- 期刊/SSRN/arXiv: Journal of Banking & Finance
- 链接: https://doi.org/10.1016/j.jbankfin.2025.107556
- 研究主题: volatility hedging、VIX futures demand、SPX futures impact
- 原论文公式:
  - 论文核心可观测量是 `D_t^{ETP}`，即 VIX ETP issuer rebalancing demand。
  - 文中图 7 明确写“estimated coefficient on `D_t^{ETP}` from Eq. (10)”。
  - 早前相关文献中，文摘还给出过 `NGP = Σ gamma_i * position_i * multiplier_i` 的净 gamma 持仓表述。
- 原论文阈值/分类规则:
  - 自变量按均值和标准差标准化。
  - 论文未提供固定通用阈值。
- 适用前提:
  - 需要可识别的机械再平衡需求与做市商对冲渠道。
- 对应仓库指标:
  - `net_gex`
  - `zero_gamma_level`
  - `gamma_flip`
  - `FLOW_D`
- 解释性摘要:
  - 这篇论文再次说明，学术中的“hedging pressure”来自真实净仓位或可识别机械需求。
  - 它支持仓库用 gamma sign 做方向判断，但不支持把 `volume * gamma * S^2` 说成标准学术流量公式。

## 7. Retail option traders and the implied volatility surface

- 标题: Retail option traders and the implied volatility surface
- 作者: Gregory W. Eaton, T. Clifton Green, Brian S. Roseman, Yanbin Wu
- 年份: 2026
- 期刊/SSRN/arXiv: Journal of Financial Economics
- 链接: https://doi.org/10.1016/j.jfineco.2026.104238
- 研究主题: retail demand pressure、IV term structure、moneyness curve、call-put spread
- 原论文公式:
  - 论文核心设计是用 brokerage outages 作为 exogenous demand shocks。
  - 结果层面关心 implied volatility 在 term structure、moneyness curve、call-put spread 上的变化，而非单一 closed-form smile factor。
- 原论文阈值/分类规则:
  - 论文未给固定通用阈值。
  - 主要区分 short-dated / long-dated、OTM / other buckets、call / put。
- 适用前提:
  - 适用于 demand shock 对 IV surface 的因果识别。
- 对应仓库指标:
  - `iv_velocity`
  - `svol_corr`
  - `svol_state`
  - `skew_25d_normalized`
  - `iv_regime`
- 解释性摘要:
  - 论文支持“IV surface 是需求驱动的，并体现在期限结构、moneyness curve 和 call-put spread 上”。
  - 但它不支持仓库当前的状态机阈值，也不提供统一的 `svol_state` 或 `iv_regime` 门槛。

## 8. Decomposing informed trading in equity options

- 标题: Decomposing informed trading in equity options
- 作者: Felipe Asencio, Alejandro Bernales, Daniel González, Richard Holowczak, Thanos Verousis
- 年份: 2026
- 期刊/SSRN/arXiv: Journal of Econometrics
- 链接: https://doi.org/10.1016/j.jeconom.2025.106131
- 研究主题: option order flow、delta/vega decomposition、volatility-informed trading
- 原论文公式:
  - 论文建立 multi-asset model，把 option spread 分解为:
    - stock-value component `θ_i^S`
    - volatility component `θ_i^σ`
    - inventory component `γ_i`
  - 结果实现部分写明这些量来自 Eqs. `(18)-(20)`。
  - `Δt = 5 seconds` 作为做市商更新报价的评价窗口。
- 原论文阈值/分类规则:
  - 非固定阈值模型。
  - 经验发现:
    - stock-value component 平均占 spread 的 41%
    - volatility component 平均占 19%
    - potential straddles 的 volatility-informed trading 高 136%
- 适用前提:
  - 需要高频 OPRA tick、quote、delta、vega。
  - 适用于“不同合约 delta/vega price responses”可识别的微结构环境。
- 对应仓库指标:
  - `FLOW_D`
  - `FLOW_E`
  - `FLOW_G`
  - `iv_velocity`
  - `vanna_flow_result`
- 解释性摘要:
  - 这篇论文最接近“option flow academic microstructure”。
  - 它支持 delta/vega 维度上分解流量信息，但并没有给出仓库 `FLOW_D/E/G` 这三条 exact 合成公式。

## 9. 跨论文提炼出的审计准则

- 基础 Greeks:
  - 近期论文仍默认标准 option-sensitivity 体系，不会给出新的固定阈值。
- GEX / dealer hedging:
  - 近期论文更偏向真实净仓位、真实 demand shock、可识别做市商 hedging channel。
  - 公开 OI 口径只能算 proxy。
- 25-delta skew:
  - `25Δ` 选腿本身有文献与市场惯例支撑。
  - 但不同论文和市场有符号约定差异，且通常不再除以 ATM IV。
- VRP:
  - 标准思路是 risk-neutral vs physical/realized volatility 的差。
  - 用固定 baseline-HV 常数只能是工程近似。
- option flow / OI / volume:
  - 学术上承认其信息含量。
  - 但 exact composite formula 往往不是统一标准，而是样本内建模选择。

## 10. 源手册使用方式

- 用本文件判断“概念是否有论文支撑”。
- 用 `docs/OPTION_PAPER_FORMULA_AUDIT_2024_2026.md` 判断“仓库实现是否与论文一致、部分一致、或仅是工程 proxy”。
- 当某指标在本文件中仅有“方向性支撑”而没有统一公式时，仓库文档必须写:
  - `仓库工程派生，不是标准学术定义`
  - `论文未提供固定通用阈值`

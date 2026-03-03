# L1 — 本地计算层 (Local Computation Layer)

> **职责**: 对 L0 拉取的原始报价进行本地 BSM 计算，生成完整的 Greeks 数据和聚合指标（Net GEX / Net Vanna / Net Charm / Gamma Walls），并向 L2 暴露经过丰富的快照。

---

## 1. 核心设计原则

| 原则 | 实现方式 |
|------|----------|
| **无外部依赖** | 所有 Greeks 均通过本地 BSM 公式计算，不调用 Longport 的 Greeks 字段（仅作参考备用） |
| **单次遍历** | `_enrich_chain_with_local_greeks` 遍历链一次，同时更新单合约 Greeks 并累加聚合值 |
| **Sticky-Strike 修正** | 对 IV 应用 skew 调整，消除 spot 漂移引起的 IV 系统偏差 |
| **IV 双轨路径** | `WS 实时 IV > REST 缓存 IV`，保证计算时始终使用最新 IV |

---

## 2. BSM 计算流程

```
对链中每个合约:

1. IV 选取
   └─ WS 实时 IV (entry["implied_volatility"])
      OR REST 缓存 IV (iv_sync.iv_cache[symbol])

2. Sticky-Strike 修正
   └─ skew_adjust_iv(cached_iv, spot_now, spot_at_sync, opt_type)
      → adjusted_iv

3. BSM Greeks 计算
   └─ compute_greeks(spot, strike, adjusted_iv, t_years, opt_type, r, q)
      → {delta, gamma, theta, vega, vanna, charm, ...}

4. GEX 贡献（单次累积）
   GEX_i = Gamma_i × OI_i × Spot² × Multiplier × 0.01
   CALL: agg["net_gex"] += GEX_i
   PUT:  agg["net_gex"] -= GEX_i

5. 暴露度累积
   vanna_exp = vanna_i × OI_i × Multiplier
   charm_exp = charm_i × OI_i × Multiplier
```

**时间衰减参数**: `get_trading_time_to_maturity(now)` → 使用交易时间（而非日历时间）计算 TTM，精确到 0DTE 当日剩余交易秒数。

---

## 3. 聚合输出 (`aggregate_greeks`)

```python
{
    "net_gex":          float,   # 净 Gamma 敞口（百万美元）
    "net_vanna":        float,   # 净 Vanna 敞口
    "net_charm":        float,   # 净 Charm 敞口
    "total_call_gex":   float,   # 做市商 Call 端 GEX（正）
    "total_put_gex":    float,   # 做市商 Put 端 GEX（负）
    "call_wall":        float,   # GEX 最大的 Call strike（阻力位）
    "put_wall":         float,   # GEX 最大的 Put strike（支撑位）
    "max_call_gex":     float,
    "max_put_gex":      float,
}
```

> GEX 单位归一化: 原始值 ÷ 1,000,000 → **百万美元**

---

## 4. Skew 调整 (`skew_adjust_iv`)

```
scenario: spot 从 IV 同步时向上移动 Δs
调整规则:
  CALL: adjusted_iv = base_iv - skew_slope × Δs   (skew 右倾，看涨期权 IV 略降)
  PUT:  adjusted_iv = base_iv + skew_slope × Δs   (skew 左倾，看跌期权 IV 略升)
```

这实现了简化版 Sticky-Strike 模型，防止在 spot 位移时系统性高估/低估 OTM 期权 GEX。

---

## 5. Greeks Extractor (`agents/services/greeks_extractor.py`)

`GreeksExtractor.compute()` 接收链数据后进行二次聚合，产出 AgentB1 决策所需的高级指标：

| 输出字段 | 含义 |
|---------|------|
| `atm_iv` | ATM 合约的隐含波动率 |
| `spy_atm_iv` | 同上（别名，用于 UI） |
| `net_gex` | 来自 `aggregate_greeks`，单位 $M |
| `gamma_walls` | `{call_wall, put_wall}` |
| `gamma_flip` | bool：Net GEX 是否为负 |
| `gamma_flip_level` | GEX 符号翻转的临界 strike |
| `gamma_profile` | 每个 strike 的 GEX（用于 Depth Profile 图） |
| `per_strike_gex` | 同上（别名） |
| `charm_exposure` | 净 Charm 敞口（时间衰减方向指示） |
| `skew_25d` | `{call_25d_iv, put_25d_iv}`（25-Delta skew） |

---

## 6. 时间到期计算 (`bsm.py` → `get_trading_time_to_maturity`)

```python
# 0DTE 精确计算:
今天还剩多少交易秒 = 到 16:00 ET 的秒数（不含收盘后）
t_years = 剩余秒数 / (252 × 6.5 × 3600)
```

该函数是"时间炸弹"的核心：随着收盘临近，TTM → 0，Gamma 急速膨胀，GEX 绝对值增大。

---

## 7. 关键文件

| 文件 | 职责 |
|------|------|
| `services/feeds/option_chain_builder.py` | `_enrich_chain_with_local_greeks()` — BSM 丰富 + 聚合 |
| `services/analysis/bsm.py` | BSM 公式：`compute_greeks`, `skew_adjust_iv`, `get_trading_time_to_maturity` |
| `agents/services/greeks_extractor.py` | 聚合 → 高级指标（ATM IV、Walls、Gamma Profile） |
| `services/feeds/iv_baseline_sync.py` | `iv_cache` / `oi_cache` 提供 IV 和 OI 给 BSM |

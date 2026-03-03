# L0 — 数据摄取层 (Data Ingestion Layer)

> **职责**: 从 Longport OpenAPI 采集 SPY 现货价格 + 期权链报价，维护内存中的合约字典，并向上层暴露零等待的快照接口。

---

## 1. 核心设计原则

| 原则 | 实现方式 |
|------|----------|
| **零等待快照** | `fetch_chain()` 直接读取内存字典，不发起任何 REST 请求 |
| **线程安全** | Longport SDK 在 OS 线程回调；通过 `loop.call_soon_threadsafe` 路由到 asyncio 线程再写字典 |
| **速率保护** | `APIRateLimiter`（令牌桶 8 req/s, burst 8, max_concurrent 4）注入所有 REST 调用点 |
| **分层订阅** | 三层订阅策略，在 API 配额与数据粒度间做最优权衡 |

---

## 2. 订阅分层架构

### Tier 1 — WebSocket 实时推送 (`SubscriptionManager`)
- **触发**: 常驻订阅，SPY 现货 + 0DTE/1DTE 期权合约
- **窗口**: ATM ± 动态 strike window（`settings.strike_window_size`）
- **数据**: 
  - `SubType.Quote`: Bid/Ask/Last/Volume/IV/Greeks（1Hz - 实时）
  - `SubType.Depth`: **Orderbook L1 深度**（买卖价量，用于 BBO Imbalance）
  - `SubType.Trade`: **逐笔成交**（包含成交方向，用于 Toxicity Score）
- **写入路径**: OS线程 → `_on_quote_callback` → `call_soon_threadsafe` → `_safe_on_quote` → `_chain[symbol]`

### Tier 2 — 2DTE REST 轮询 (`Tier2Poller`)
- **触发**: 独立后台线程，每 120s 轮询一次
- **窗口**: ATM ± 30 点
- **数据**: 补充最近到期日（2DTE）的 Option Quote 快照
- **写入位置**: `self._tier2.cache`（`fetch_chain` 时附加到 `tier2_chain`）

### Tier 3 — 周期权 REST 轮询 (`Tier3Poller`)
- **触发**: 每 10min 轮询一次
- **筛选**: Top 20 OI 合约
- **数据**: 周期权仓位分布，用于宏观 GEX 补充
- **写入位置**: `self._tier3.cache`（`fetch_chain` 时附加到 `tier3_chain`）

---

## 3. IV 基线同步 (`IVBaselineSync`)

```
REST 轮询 (每 120s, 2-chunk 交错)
    └─→ 每个 symbol 的 REST IV / OI → iv_cache / oi_cache

WS 推送 (实时)
    └─→ apply_iv_update(symbol, iv, oi) → 覆盖缓存（WS 优先）
```

**IV 优先级**: `WS 实时 IV > REST 缓存 IV`

当 WS 没有 IV 数据（期权未成交）时，回退到 REST 缓存。

---

## 4. 管理循环 (`_management_loop`)

每 60 秒运行：

1. **现货兜底**: 如果 WS 超过 10s 未更新 spot，通过 REST 补拉 `SPY.US` quote
2. **订阅刷新**: 调用 `SubscriptionManager.refresh()` 重新计算 target_symbols。
   - **L2 Policy**: 对成交量前 10 的 ATM 近端期权开启 `SubType.Depth` 和 `SubType.Trade`。
3. **IV 暖启动**: 对新订阅的 symbol 调用 `IVBaselineSync.warm_up()` 预填缓存。
4. **量研究**: 每 15 min 执行 `_run_volume_research`，宽窗口扫描所有 strike 的成交量，生成 `volume_map`

---

## 5. 数据输出格式

`fetch_chain()` 返回：

```python
{
    "spot": float,                 # SPY 现货价格
    "chain": list[dict],           # Tier1 已订阅合约列表（含 WS 最新报价）
    "tier2_chain": list[dict],     # 2DTE 合约快照
    "tier3_chain": list[dict],     # 周期权快照
    "volume_map": dict[float,int], # strike → 总成交量
    "aggregate_greeks": dict,      # BSM 单次聚合结果（见 L1）
    "as_of": datetime,
}
```

---

## 6. 速率限制器 (`APIRateLimiter`)

```
令牌桶参数:
  rate         = 8.0 req/s
  burst        = 8
  max_concurrent = 4

触发 cooldown: 收到错误码 301607 (API 超额) 时激活节流
动态区间:  根据当前可用 token 数反馈给 compute loop，在 1~3s 间动态调整
```

所有 REST 调用必须通过 `async with self._rate_limiter.acquire()` 包裹，**不允许裸 sleep 重试**。

---

## 7. 关键文件

| 文件 | 职责 |
|------|------|
| `services/feeds/option_chain_builder.py` | L0 总调度器，WS 回调，`fetch_chain()` |
| `services/feeds/subscription_manager.py` | Tier1 动态订阅管理 |
| `services/feeds/iv_baseline_sync.py` | IV/OI REST 基线 + WS 覆盖 |
| `services/feeds/tier2_poller.py` | 2DTE REST 轮询 |
| `services/feeds/tier3_poller.py` | 周期权 REST 轮询 |
| `services/feeds/rate_limiter.py` | 全局令牌桶速率限制 |
| `services/system/persistent_oi_store.py` | OI 持久化（跨会话） |

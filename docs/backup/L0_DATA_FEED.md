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

## 4. 模块化重构 (OptionChainBuilder 分拆)

原先的单体 `OptionChainBuilder` 已重构为 5 个职责单一的组件：

1. **`MarketDataGateway`**: 唯一的 WebSocket 连接入口与生命周期管理者。接收 OS 线程回调，并统一路由至 asyncio 队列，消除了线程竞争。
2. **`SanitizationPipeline`**: L1A 数据清洗边界。集中执行所有 `float()` 映射与 `math.isfinite()` 校验，确保进入系统的所有数据（去除 NaN/Inf 等）均为安全的强类型事件（如 `CleanQuoteEvent`）。
3. **`ChainStateStore`**: 内存链状态序列化存储（L1B）。引入了 **Sequence Number (seq_no)** 机制，防止旧的 REST 轮询数据覆盖这新鲜的 WS 推送。提供 `apply_event()` 与只读的 `get_snapshot()`。
4. **`GreeksEngine`**: 离线计算引擎（详见 L1 文档）。
5. **`FeedOrchestrator`**: 行政调度员。全权管理原有的 `_management_loop`：现货兜底、Tier 1 订阅刷新、IV 暖启动、以及 15 分钟级的宽窗口成交量扫描。

通过这种解耦，`OptionChainBuilder` 演变为了一个精简的引导整合层，只负责连接这些核心组件。

---

## 5. 数据输出格式

`fetch_chain()` 提取经流程清洗、计算聚合后的最新数据并返回：

```python
{
    "spot": float,                 # SPY 现货价格
    "chain": list[dict],           # Tier1 已订阅合约列表（含 WS 最新报价、Greeks、深口盘口）
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
| `services/feeds/option_chain_builder.py` | L0 总调度器，仅作为各个分离模块的外壳 |
| `services/feeds/market_data_gateway.py` | WebSocket 连接池，唯一的跨线程 asyncio 消息队列 |
| `services/feeds/sanitization.py` | 数据清理白名单，所有 NaN/Inf 及类型强转收口 |
| `services/feeds/chain_state_store.py` | 单写多读的 `_chain` 存储，附带 seq_no 版本控制 |
| `services/feeds/feed_orchestrator.py` | 管理调度循环，订阅刷新与定时研究任务 |
| `services/feeds/subscription_manager.py` | Tier1 动态订阅管理 |
| `services/feeds/iv_baseline_sync.py` | IV/OI REST 基线 + WS 覆盖 |
| `services/feeds/tier2_poller.py` | 2DTE REST 轮询 |
| `services/feeds/tier3_poller.py` | 周期权 REST 轮询 |
| `services/feeds/rate_limiter.py` | 全局令牌桶速率限制 |
| `services/system/persistent_oi_store.py` | OI 持久化（跨会话），现在通过 IVBaselineSync 初始化 |

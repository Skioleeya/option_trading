# l0_ingest — L0 数据摄入层

> **职责**：从交易所原始行情流（LongPort WS + REST Tier2/3 轮询）拉取数据，经过清洗、限流，输出稳定的期权链快照供 L1 使用。

## 架构总览

```
l0_ingest/
├── feeds/                    # 核心生产管线
│   ├── option_chain_builder.py  # 顶层编排（主入口，fetch_chain()）
│   ├── market_data_gateway.py   # LongPort WS 连接管理（quote_ctx 单例）
│   ├── feed_orchestrator.py     # 主动合约发现 + 订阅级联
│   ├── subscription_manager.py  # WS subscriptions 生命周期
│   ├── chain_state_store.py     # REST/WS 双写快照存储（价格字段优先级保护）
│   ├── iv_baseline_sync.py      # IV 基线同步（REST → WS 降级，spot_at_sync TTL）
│   ├── sanitization.py          # L0 清洗管线（无套利条件 + 报价时效 TTL）
│   ├── rate_limiter.py          # Token Bucket + Semaphore + 冷却期一体限流器
│   ├── tier2_poller.py          # Tier2 品种轮询（次 ATM 档位）
│   ├── tier3_poller.py          # Tier3 品种轮询（深度 OTM / OI 精排）
│   ├── longport_adapter.py      # WS 心跳检测 + 指数退避重连
│   └── base_feed.py             # FeedBase 协议接口
├── events/                   # 强类型事件 (CleanQuoteEvent, CleanDepthEvent…)
├── sanitize/                 # SanitizePipelineV2 + StatisticalBreaker
├── store/                    # MVCCChainStateStore（版本化快照隔离）
├── rate_governor/            # 4 层自适应限流（TokenBucket + SlidingWindow + CircuitBreaker + Priority）
├── quality/                  # DataQualityReport + QualityCollector
├── observability/            # OTel + Prometheus 桩（无依赖时 graceful fallback）
└── tests/                    # pytest 套件
```

## 快速使用

```python
from l0_ingest.feeds.option_chain_builder import OptionChainBuilder

builder = OptionChainBuilder()
await builder.initialize()           # 建立 WS 连接，启动限流器
snapshot = await builder.fetch_chain()  # 返回 { "chain": [...], "spot": 685.0 }
await builder.shutdown()
```

## 限流规格

`rate_limiter.py` 使用 **SingletonRateLimiter**，全局唯一实例保证：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_calls` | 10 | 每秒最大调用次数 |
| `max_concurrent` | 5 | 最大并发请求数 |
| `cooldown_s` | 60 | 触发限流后冷却期 |

OI 与 IV REST 源均受同一实例约束，防止并发爆发。

## L0 清洗规则（`sanitization.py`）

| 规则 | 参数 | 说明 |
|------|------|------|
| **无套利条件** | `call_iv > put_iv + 0.05` @ 同 strike | 过滤穿透报价 |
| **报价时效 TTL** | `quote_age > 300s` | 过期报价标记为无效 |
| **Bid/Ask 合理性** | `bid > ask` | 倒挂报价丢弃 |
| **OI 突变检测** | `delta > 5σ` | 极端 OI 跳变过滤 |

## IV 降级链（`iv_baseline_sync.py`）

```
WS 实时 IV（TTL 满足）
  ↓ 过期/缺失
REST 基线 IV（spot_at_sync 检验）
  ↓ 基线无效
Chain 中位 IV
  ↓ 无链数据
SABR 外推（L1 层接管）
```

## 关键组件

| 组件 | 说明 |
|------|------|
| `chain_state_store.py` | WS 价格字段保护：REST 仅补充，不覆盖 WS 实时价格 |
| `iv_baseline_sync.py` | `spot_at_sync` 双 TTL 检验（有效 IV 时才更新基线 spot） |
| `sanitization.py` | 无套利条件过滤 + 报价时效 TTL |
| `rate_limiter.py` | Singleton Token Bucket，冷却后 token 受限（防爆发） |
| `tier2_poller.py` | 次 ATM 档位定时补充，Tier3 深度 OTM 精排 |

## 运行测试

```bash
python -m pytest l0_ingest/tests/ -v --tb=short
```

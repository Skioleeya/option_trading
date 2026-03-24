# l0_ingest — L0 数据摄入层

> **职责**：从交易所原始行情流（LongPort WS + REST Tier2/3 轮询）拉取数据，经过清洗、限流，输出稳定的期权链快照供 L1 使用。

## 架构总览

```
l0_ingest/
├── v2/                       # 唯一正式运行树
│   ├── facade.py                # app 唯一入口，initialize/fetch_snapshot/shutdown
│   ├── source/runtime/          # Quote runtime, LongPort gateway, OpenAPI bootstrap, limiter
│   ├── normalize/               # WS/REST/SHM 标准化、事件桥接、清洗
│   ├── state/runtime/           # ChainStateStore + LiveState
│   ├── services/                # subscription/orchestration/sync/repair/pollers/runtime
│   ├── projection/snapshot/     # snapshot payload + diagnostics projection
│   └── contracts/               # facade 小型 contract / callback hooks
├── events/                   # 强类型事件 (CleanQuoteEvent, CleanDepthEvent…)
├── sanitize/                 # SanitizePipelineV2 + StatisticalBreaker
├── store/                    # MVCCChainStateStore（版本化快照隔离）
├── rate_governor/            # 4 层自适应限流（TokenBucket + SlidingWindow + CircuitBreaker + Priority）
├── quality/                  # DataQualityReport + QualityCollector
├── observability/            # OTel + Prometheus 桩（无依赖时 graceful fallback）
└── tests/
    ├── v2/                   # V2 runtime 回归
    └── *.py                  # 其余中立/基础模块回归
```

## 快速使用

```python
from l0_ingest.v2 import OptionChainBuilder

builder = OptionChainBuilder()
await builder.initialize()           # 建立 WS 连接，启动限流器
snapshot = await builder.fetch_snapshot()  # 返回 { "chain": [...], "spot": 685.0 }
await builder.shutdown()
```

## 限流规格

`v2/source/runtime/rate_limiter.py` 使用统一 `APIRateLimiter`，全局唯一配置保证：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_calls` | 10 | 每秒最大调用次数 |
| `max_concurrent` | 5 | 最大并发请求数 |
| `cooldown_s` | 60 | 触发限流后冷却期 |

OI 与 IV REST 源均受同一实例约束，防止并发爆发。

## L0 清洗规则（`v2/normalize/pipeline/sanitization.py`）

| 规则 | 参数 | 说明 |
|------|------|------|
| **无套利条件** | `call_iv > put_iv + 0.05` @ 同 strike | 过滤穿透报价 |
| **报价时效 TTL** | `quote_age > 300s` | 过期报价标记为无效 |
| **Bid/Ask 合理性** | `bid > ask` | 倒挂报价丢弃 |
| **OI 突变检测** | `delta > 5σ` | 极端 OI 跳变过滤 |

## IV 降级链（`v2/services/sync/iv_baseline_sync.py`）

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
| `v2/state/runtime/chain_state_store.py` | WS 价格字段保护：REST 仅补充，不覆盖 WS 实时价格 |
| `v2/services/sync/iv_baseline_sync.py` | `spot_at_sync` 双 TTL 检验（有效 IV 时才更新基线 spot） |
| `v2/normalize/pipeline/sanitization.py` | 无套利条件过滤 + 报价时效 TTL |
| `v2/source/runtime/rate_limiter.py` | Token Bucket + 并发 + cooldown 一体限流 |
| `v2/services/pollers/*.py` | Tier2/Tier3 档位轮询 |

## 运行测试

```bash
python -m pytest l0_ingest/tests/ -v --tb=short
```

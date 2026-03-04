# l0_ingest — L0 数据摄入层重构包

> **Strangler Fig 模式** — 与 `backend/app/services/feeds/` 并存，验证通过后逐步替换。

## 架构总览

```
l0_ingest/
├── events/          # 强类型事件 (CleanQuoteEvent v2, CleanDepthEvent v2…)
├── sanitize/        # SanitizePipelineV2 + StatisticalBreaker
├── store/           # MVCCChainStateStore (版本化快照隔离)
├── rate_governor/   # 4 层自适应限流 (TokenBucket + SlidingWindow + CircuitBreaker + Priority)
├── quality/         # DataQualityReport + QualityCollector
├── observability/   # OTel + Prometheus 桩 (无依赖时 graceful fallback)
├── feeds/           # MarketFeed Protocol + LongportFeedAdapter
└── tests/           # pytest 套件 (52 测试, 100% 通过)
```

## 快速开始

```python
from l0_ingest.sanitize import SanitizePipelineV2
from l0_ingest.store import MVCCChainStateStore

pipeline = SanitizePipelineV2(enable_statistical_check=True)
store = MVCCChainStateStore()

# 解析 + 质量报告
event, report = pipeline.parse_with_quality(raw_dict, event_hint="quote")
if event:
    store.apply_quote(event)

# 线程安全读取
version, snapshot = store.get_snapshot()
```

## 向后兼容 API

`SanitizePipelineV2` 保留与 `SanitizationPipeline` 相同的入口：

```python
pipeline.parse_quote(raw)   # → CleanQuoteEvent | None
pipeline.parse_depth(raw)   # → CleanDepthEvent | None
pipeline.parse_trade(raw)   # → CleanTradeEvent | None
```

## 切换方式

在 `option_chain_builder.py` 顶部更改 import：

```python
# 旧
from l0_ingest.feeds.sanitization import SanitizationPipeline

# 新
from l0_ingest.sanitize import SanitizePipelineV2 as SanitizationPipeline
```

## 运行测试

```bash
cd e:\US.market\Option_v3
python -m pytest l0_ingest/tests/ -v --tb=short
```

## 关键组件说明

| 组件 | 改进点 |
|------|-------|
| `StatisticalBreaker` | Tick Jump (5σ) + Gap + bid>ask + OI突变，Q99 计算在追加当次值之**前**，避免自掩蔽 bug |
| `MVCCChainStateStore` | 写时复制快照，读取端无锁，历史版本 GC |
| `AdaptiveRateGovernor` | 4 层：TokenBucket + SlidingWindow + CircuitBreaker + Priority |
| `LongportFeedAdapter` | 心跳检测 + 指数退避重连，同步接入 SanitizePipelineV2 |
| `L0Instrumentation` | OTel/Prometheus 可选依赖，无包时 no-op 回退 |

## Phase 路线图

- **Phase 1 (本次)**: Python 层全部组件 ✅
- **Phase 2**: Rust IngestWorker (零拷贝消费 event_queue)
- **Phase 3**: 逐步替换 `option_chain_builder.py` import

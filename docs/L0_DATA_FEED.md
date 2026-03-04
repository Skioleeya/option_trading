# L0 — 数据摄取层 (Data Ingestion Layer)

## 2025–2026 主流金融架构重构指引

> **定位**: L0 是系统的感官神经元——负责以亚毫秒延迟从市场数据源（Longport / Polygon / Databento / OPRA）采集报价流，完成**数据归一化 → 质量断言 → 有序分发**三阶段处理后，以强类型事件流形式交付给 L1。
>
> **架构宗旨 (2025–2026)**: 从"轮询 + 回调"单体模式，全面迁移至 **Event-First Architecture + FPGA-Ready Interface + Observability-Native Design**。

---

## 1. 架构目标与度量标准

| KPI | 当前基线 (v3) | 2025 H2 目标 | 2026 目标 |
|-----|--------------|-------------|----------|
| WS → 内存快照延迟 | ~5–15 ms | **< 1 ms** (Rust ingest) | **< 200 µs** (kernel bypass) |
| REST 回退 p99 延迟 | 150–300 ms | < 80 ms (连接池复用) | < 50 ms (gRPC streaming) |
| 内存快照一致性 | seq_no 乐观锁 | **MVCC 快照隔离** | 无锁 SPSC ring buffer |
| 数据质量覆盖率 | NaN/Inf 清洗 | **统计异常断路器** | 自适应 Z-Score 门限 |
| 可观测性 | print 日志 | **OpenTelemetry spans** | 全链路 tick-to-trade |

---

## 2. 事件驱动摄取架构 (Target State)

```
                    ┌──────────────────────────────────────────────────┐
                    │               L0 Data Ingestion Mesh             │
                    │                                                  │
  ┌──────────┐      │  ┌──────────────┐   ┌────────────────┐          │
  │ Longport │──WS──│─▶│ IngestWorker │──▶│ SanitizePipe   │          │
  │ OPRA     │      │  │  (Rust/Tokio)│   │ (Type+Stat)    │          │
  │ Polygon  │──WS──│─▶│              │   └───────┬────────┘          │
  │ Databento│      │  └──────────────┘           │                   │
  └──────────┘      │                    ┌────────▼────────┐          │
                    │                    │ EventBus (SPSC) │          │
                    │                    │ Ring Buffer      │          │
                    │                    └────────┬────────┘          │
                    │              ┌──────────────┼───────────────┐   │
                    │              ▼              ▼               ▼   │
                    │      ChainStateStore  TimeSeriesLog   OTel Span │
                    │      (MVCC Snapshot)  (Parquet/Arrow) (Traces)  │
                    └──────────────────────────────────────────────────┘
```

### 2.1 IngestWorker (Rust/Tokio)

替代当前 Python OS 线程回调:

```rust
// 伪代码 — Rust ingest worker
async fn ingest_loop(ws: WsStream, bus: SpscProducer<MarketEvent>) {
    while let Some(frame) = ws.next().await {
        let event = decode_longport_frame(frame)?;  // 零拷贝解码
        let clean = sanitize(event)?;                // 内联 NaN/Inf 检查
        bus.push(clean);                             // 无锁分发
        OTEL_COUNTER.add(1, &[("feed", "longport")]); // 可观测性
    }
}
```

**关键改进**:
- **零拷贝解码**: 使用 `rkyv` 或 Cap'n Proto 直接映射 wire bytes → struct，消除 Python `float()` 转换开销
- **背压 (Backpressure)**: Ring buffer 满时丢弃最旧报价而非阻塞生产者，保证延迟确定性
- **多源汇聚**: 统一 trait `MarketFeed` 抽象 Longport / Polygon / Databento，一条 ingest 通道服务多源

### 2.2 SanitizePipeline 2.0

从简单 NaN/Inf 清洗升级为**统计异常检测**:

| 检测维度 | 当前 | 2025–2026 目标 |
|---------|------|---------------|
| 数值有效性 | `math.isfinite()` | 保留 + 下游 Z-Score 断路器 |
| 价格跳变 | 无 | **Tick-to-tick ΔP > 5σ → circuit breaker** |
| 时间序列断流 | 无 | **Gap > 3s → 触发 REST backfill** |
| Bid/Ask 倒挂 | 无 | **Crossed market detection** → 标记 `is_stale` |
| OI 异常飙升 | 无 | **OI delta > Q99 → alert + snapshot** |

### 2.3 ChainStateStore 2.0 — MVCC 快照隔离

替代当前 seq_no 乐观锁：

```python
class ChainStateStore:
    """Multi-Version Concurrency Control for market state"""

    def apply_event(self, event: CleanQuoteEvent) -> None:
        """写入新版本（仅在 ingest 线程调用）"""
        new_version = self._current_version + 1
        self._versions[new_version] = {
            **self._versions[self._current_version],
            event.symbol: event.to_dict()
        }
        self._current_version = new_version
        self._gc_old_versions(keep=3)

    def get_snapshot(self) -> tuple[int, dict]:
        """读取最新一致性快照（任意线程安全调用）"""
        v = self._current_version  # atomic read
        return v, self._versions[v]  # 不可变引用
```

**优势**: 读者永远看到一致的点快照，无锁竞争。GC 保留最近 3 个版本支持偶发延迟读。

---

## 3. 分层订阅架构 2.0

### Tier 0 — FPGA / Kernel Bypass (2026 Vision)

| 属性 | 规格 |
|------|------|
| 协议 | OPRA/SIP 原始 multicast (UDP) |
| 延迟 | < 10 µs (hardware timestamped) |
| 部署 | Colo 机房 + Solarflare NIC |
| 适用 | 超低延迟 HFT 场景扩展 |

> ⚠️ **2025 路线**: 设计接口抽象但不实现硬件层；保证软件架构不阻塞未来硬件升级。

### Tier 1 — WebSocket 实时推送 (核心)

- **协议**: Longport WS (Quote + Depth + Trade)
- **改进**: Rust IngestWorker 接管 OS 线程回调
- **窗口**: ATM ± 动态 window（保持）
- **新增**: 心跳监控 + 自适应重连退避 (exponential backoff with jitter)

### Tier 2 — 近到期 REST 轮询

- **改进**: HTTP/2 connection multiplexing
- **新增**: 条件轮询 — 仅在 Tier 1 gap > 3s 时触发
- **格式**: 响应转 Arrow RecordBatch 减少 GC 压力

### Tier 3 — 宏观结构 REST (周期权)

- **保持**: 10min 轮询 Top-20 OI
- **新增**: 增量模式 — 仅拉取 OI 变化 > 5% 的合约

---

## 4. 速率限制器 2.0

```
┌─────────────────────────────────────────────────┐
│           Adaptive Rate Governor                 │
│                                                  │
│  Layer 1: Token Bucket (8 req/s, burst 8)       │ ← 保持
│  Layer 2: Sliding Window (per-endpoint)          │ ← 新增
│  Layer 3: Circuit Breaker (3 consecutive 429)    │ ← 新增
│  Layer 4: Priority Queue (Quote > OI > History)  │ ← 新增
│                                                  │
│  Metrics: p50/p99 latency, rejection rate,       │
│           token utilization → OTel Histogram     │
└─────────────────────────────────────────────────┘
```

---

## 5. 数据输出格式 2.0 (Arrow-Native)

```python
# 2025 目标: 从 dict-of-dicts 迁移至 Apache Arrow RecordBatch
{
    "spot": float,                          # SPY 现货价格
    "chain": pa.RecordBatch,                # Tier1 合约 (zero-copy to L1)
    "tier2_chain": pa.RecordBatch,          # 2DTE 合约
    "tier3_chain": pa.RecordBatch,          # 周期权
    "volume_map": dict[float, int],         # strike → 总成交量
    "aggregate_greeks": dict,               # BSM 聚合 (L1 产出)
    "as_of": datetime,
    "version": int,                         # MVCC 版本号
    "quality": DataQualityReport,           # 新增: 数据质量诊断
}
```

---

## 6. 可观测性 (Observability-Native)

| 维度 | 工具 | 指标 |
|------|------|------|
| Traces | OpenTelemetry → Jaeger | 每个 tick 的 ingest→sanitize→store 完整链路 |
| Metrics | Prometheus Histogram | `l0_ingest_latency_us`, `l0_sanitize_rejects_total` |
| Logs | Structured JSON (slog) | 所有异常事件带 `trace_id` 关联 |
| Alerts | Grafana Alert Rules | Gap > 5s, rejection_rate > 1%, latency p99 > 10ms |

---

## 7. 迁移路线图

```
Phase 1 (2025 Q3): SanitizePipeline 统计断路器 + OTel instrumentation
Phase 2 (2025 Q4): Rust IngestWorker (tokio WS) + SPSC EventBus
Phase 3 (2026 Q1): MVCC ChainStateStore + Arrow RecordBatch 输出
Phase 4 (2026 Q2): 多源 Feed 抽象 (Polygon/Databento) + 条件轮询
Phase 5 (2026 H2): FPGA/Kernel Bypass 接口预留
```

---

## 8. 关键文件（当前 → 目标映射）

| 当前文件 | 重构目标 | 备注 |
|---------|---------|------|
| `services/feeds/option_chain_builder.py` | 精简为纯 Orchestrator Shell | 逻辑全部下沉子模块 |
| `services/feeds/market_data_gateway.py` | → Rust `ingest_worker` | PyO3 暴露 Python 接口 |
| `services/feeds/sanitization.py` | → `SanitizePipeline v2` | 增加统计异常检测 |
| `services/feeds/chain_state_store.py` | → MVCC 版本化存储 | 消除 seq_no 乐观锁 |
| `services/feeds/feed_orchestrator.py` | 保持，增加条件轮询逻辑 | — |
| `services/feeds/rate_limiter.py` | → `AdaptiveRateGovernor` | 分层限流 + 优先级 |
| — (新文件) | `otel/l0_instrumentation.py` | 可观测性桩 |
| — (新文件) | `feeds/data_quality.py` | 数据质量报告 |

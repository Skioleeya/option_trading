# L0 — 数据摄取层 (Data Ingestion Layer)

> **定位**: L0 是系统的感官神经元——负责以亚毫秒延迟从市场数据源（Longport WS/REST）采集报价流，经过**数据清洗 → 动态限流 → IV 基准提取 → MVCC 版本化存储**四阶段处理后，输出强类型的 `CleanQuoteEvent` / 链快照供 L1 消费。
>
> **架构状态 (v3.1)**: 已完成从 "长脚本混杂" 向 **模块化流水线 (Modular Pipeline)** 的重构，全面引入无套利清洗、自适应限流、以及严格的 REST 与 WS 数据覆盖保护。

---

## 1. 核心架构与处理流

```
                    ┌──────────────────────────────────────────────────┐
                    │               L0 Data Ingestion Mesh             │
                    │                                                  │
  ┌──────────┐      │  ┌──────────────┐   ┌────────────────┐          │
  │ Longport │──WS──│─▶│ MarketData   │──▶│ SanitizePipeV2 │          │
  │ WebSockets      │  │   Gateway    │   │ (Type+Stat)    │          │
  └──────────┘      │  └──────────────┘   └───────┬────────┘          │
                    │                             │                   │
  ┌──────────┐      │                     ┌───────▼────────┐          │
  │ Longport │─REST─│─▶ Tier2/3 Poller ──▶│ ChainStateStore│──▶ L1    │
  │ OpenAPI  │      │                     │ (MVCC / Protect)│          │
  └──────────┘      │                     └───────▲────────┘          │
                    │                             │                   │
                    │                     ┌───────┴────────┐          │
                    │                     │ IV Baseline    │          │
                    │                     │ Sync           │          │
                    └──────────────────────────────────────────────────┘
```

## 2. 关键组件与机制 (当前已实现)

### 2.1 数据清洗管道 (SanitizePipeV2)
从简单的 NaN/Inf 过滤升级为严密的多维断路器检测：
- **无套利条件检测**：拦截 `call_iv > put_iv + X` 同行使价穿透报价。
- **报价时效 TTL 丢弃**：拦截滞后超过预设阈值（如 300s）的延期 Tick。
- **Bid/Ask 合理性检测**：丢弃 Bid > Ask 的倒挂脏数据。
- **OI 突变护栏**：基于 `StatisticalBreaker` 拦截大于 5σ 的极端持仓量跳变。

### 2.2 链状态存储与并发保护 (MVCCChainStateStore)
当前在 `chain_state_store.py` 内部实现了针对多数据源（WS 高频 + REST 低频）的融合保护机制：
- **读写快照隔离**：保证 L1 读取时拿到点对点数据一致性（写入复制）。
- **REST 数据降权防护**：REST 轮询接口仅能补充缺失的次要期权状态，无法覆盖由 WS 创建的活跃价格字段（Bid/Ask/Spot 等）。

### 2.3 IV 基线与降级瀑布 (IV Baseline Sync)
在 0DTE 高频交易中，IV 是定价锚点。当出现流动性枯竭时，将使用以下级联降级策略求根：
1. **WS 实时 IV**（满足 TTL 有效期）
2. **REST 基线 IV**（在 `spot_at_sync` 价格有效偏离阈值内）
3. **链内中位 IV**（基于前后档推算）
4. **SABR 外推计算**（交由 L1 层计算）

### 2.4 多层限流器 (Singleton Rate Limiter)
防止在开盘、剧烈波动导致 REST 轮询雪崩：
- **Token Bucket + Semaphore**：双轨并发频控（默认 `max_calls=10/s`, `max_concurrent=5`）。
- **冷却期 (Cooldown) 阻断**：触发死锁或全局限流时进入 60s 冷却禁止访问。

## 3. 分层订阅拉取架构

- **Tier 1 (WebSocket)**：ATM 附近 ±N 档位核心合约。自动断线重连、心跳检测。
- **Tier 2 (次 ATM 轮询)**：用作 Tier1 滑动时的接力池，防踏空。
- **Tier 3 (远端 OI 轮询)**：深度 OTM 合约每 10 分钟检测，用于宏观支撑位探测。

## 4. 迁移与升级路线图 (2025-2026 Vision)

- **Phase 1 (v3.1，已完成)**：SanitizePipeline V2 统计断路器 + L0 模块化拆分 + 安全限流。
- **Phase 2 (2025 H2)**：Rust IngestWorker (tokio WS) 替代 Python 网关；引入 SPSC Ring Buffer + `rkyv` 零拷贝解码。
- **Phase 3 (2026 Q1)**：Arrow RecordBatch 完全接管字典，L0→L1 内存全透明。
- **Phase 4 (2026 H2)**：底层针对未来 FPGA/Kernel Bypass 预留协议插槽。

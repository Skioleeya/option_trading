# L0 — 数据摄取层 (Data Ingestion Layer)

> **定位**: L0 是系统的感官神经元——负责以亚毫秒延迟从市场数据源（Longport WS/REST）采集报价流，通过 **Rust Native Ingest → Zero-Copy IPC → 动态限流 → IV 修复** 四阶段处理后，输出强类型的 `CleanQuoteEvent` / 链快照供 L1 消费。
>
> **架构状态 (v4.5)**: 已完成 **Rust 混合动力升级 (Hybrid Core)**。引入了高性能 Rust Ingest Gateway 替代原生 Python WS 接收，并通过 Apache Arrow 格式实现进程间零拷贝数据传输。

---

## 1. 核心架构与处理流

```
                    ┌──────────────────────────────────────────────────┐
                    │               L0 Data Ingestion Mesh             │
                    │                                                  │
  ┌──────────┐      │  ┌──────────────┐   ┌────────────────┐          │
  │ Longport │──WS──│─▶│ Rust Ingest  │──▶│ Zero-Copy IPC  │          │
  │ WebSockets      │  │   Gateway    │   │ (Arrow Shm)    │          │
  └──────────┘      │  └──────────────┘   └───────┬────────┘          │
                    │      (Native)               │                   │
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

### 2.1 Rust Ingest Gateway (Native)
系统高性能入口，由 Rust 编写并导出 PyO3 绑定：
- **CPU 核心绑定**：通过 `affinity` 库将采集线程硬绑定至特定物理核心，消除 OS 上下文切换抖动。
- **并发异步抓取**：利用 `tokio` 运行时并行接收 WebSocket 报文。
- **原生 Threat 计算**：在接收层面直接计算 `impact_index` (OFII) 和 `is_sweep` (扫单检测)，无需通过 Python。

### 2.2 Zero-Copy IPC (Arrow Shared Memory)
解决了 L0 (Rust) 到 L1 (Python) 的传输瓶颈：
- **内存映射 (mmap)**：Python 直接访问由 Rust 预分配的 100MB 共享内存环形缓冲区。
- **SPSC Lock-Free**：单生产者单消费者模式，通过原子 head/tail 指针实现无锁同步。

### 2.3 多层限流器 (Dual-Token Bucket Rate Limiter)
针对 Longport 机构级 API 限制（错误码 301607）进行了深度重构：
- **频率限流 (Requests/sec)**：限制 REST 调用频率（默认 8/s），防止 SDK 触发惩罚。
- **容量限流 (Symbols/min)**：新增标的数量维度追踪。每分钟请求的期权标的总数严格限制在 400 个以内。
- **权重感知**：`IVSync` 批量请求 IV 时，根据 batch size 消耗对应权重的令牌，从根本上杜绝了 301607 限频错误。

### 2.4 IV 基线与降级瀑布 (IV Baseline Sync)
在 0DTE 高频交易中，IV 是定价锚点。当出现流动性枯竭时，将使用以下级联降级策略求根：
1. **WS 实时 IV**（满足 TTL 有效期）
2. **REST 基线 IV**（在 `spot_at_sync` 价格有效偏离阈值内）
3. **链内中位 IV**（基于前后档推算）
4. **SABR 外推计算**（交由 L1 层计算）

### 2.5 Gold Context (Early-Bound SDK Initialization)
针对 LongPort OpenAPI C-Core 的底层库冲突问题（当先于高性能计算库或 Rust 模块加载时会触发进程级死锁），系统实施了 **Gold Context** 初始化方案：
- **Pre-Flight 优先级**：在 `main.py` 的最早期（PRE-FLIGHT 阶段）直接初始化 `QuoteContext`，抢占全局资源位。
- **Context Injection**：初始化的 `primary_ctx` 会通过 FastAPI 的 `app.state` 缓存，并在 `AppContainer` 构建时注入到 `MarketDataGateway` 中。
- **稳定性保障**：该模式彻底解决了 GPU 负载与 SDK 连接之间的资源竞争导致的启动卡死问题。

- **Rust Path (High-Perf)**：负责处理大批量的期权链 Depth/Trade 流，由 Rust 核心直接处理并写入 SPSC 零拷贝共享内存，绕过 Python GIL 限制。
- **故障隔离与监控**：`OptionSubscriptionManager` 实现了自动双栈接力。系统现已打通全链路诊断，在 L4 仪表盘实时展现 `rust_active` 及 `shm_stats` (IPC Head/Tail) 健康指标。

### 2.6 快照版本契约 (2026-03-06 Hotfix)
为保证 SPY ATM IV 在 L1/L2 的实时一致性，L0 快照必须满足以下版本契约：
- **单调版本号**：`ChainStateStore` 维护单调递增 `version`，仅在真实状态变更时递增（spot/quote/depth/greeks/OI/volume_map）。
- **强制透传**：`OptionChainBuilder.fetch_chain()` 返回 payload 必须包含 `version`，禁止仅传业务字段不传版本。
- **失效触发语义**：下游 L1/L2 依赖该 `version` 触发缓存失效；若缺失或恒定（例如误传常量 `0`），将导致 `atm_iv` 与 `iv_velocity` 出现陈旧值滞留风险。

## 3. 分层订阅拉取架构

- **Tier 1 (WebSocket/Dual-Stack)**：ATM 附近核心合约，由 Rust Gateway 实时捕捉（Fallback 至 Python）。
- **Tier 2 (次 ATM 轮询)**：用作 Tier1 滑动时的接力池，防踏空。
- **Tier 3 (远端 OI 轮询)**：深度 OTM 合约每 10 分钟检测，用于宏观支撑位探测。

## 4. 迁移与升级路线图 (Updated 2026 Vision)

- [x] **Phase 1 (v3.1)**：L0 模块化拆分 + 安全限流。
- [x] **Phase 2 (v4.0)**：机构级数据增强。高精度 `ttm_seconds` 透传。
- [x] **Phase 3 (v4.5)**：**Rust Ingest Gateway (v1.0)**。引入 Native WS 网关 + SPSC 零锁环形队列。
- [x] **Phase 4 (v4.5)**：**301607 限频攻克**。实现加权双桶限流保护。
- [ ] **Phase 5 (2026 Q1)**：Arrow RecordBatch 完全接管字典，L0→L1 内存全透明。
- [ ] **Phase 6 (2026 H2)**：底层针对未来 FPGA/Kernel Bypass 预留协议插槽。

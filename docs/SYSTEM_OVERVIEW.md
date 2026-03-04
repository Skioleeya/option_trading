# SPY 0DTE Dashboard — 2025–2026 架构重构总览

> **系统定位**: 机构级 SPY 0DTE 期权实时决策支持平台。
>
> **文档版本**: v4.0 — 2025–2026 主流金融架构重构指引
>
> **上一版本**: 见 `docs/backup/` 目录

---

## 架构演进方向

```
┌──────────────────────────────────────────────────────────────────────┐
│  v3 (当前)                    →  v4 (2025–2026 目标)                 │
│                                                                      │
│  Python 回调 + OS 线程        →  Rust Tokio IngestWorker + EventBus  │
│  dict-of-dicts 内存模型       →  Arrow RecordBatch + MVCC            │
│  单线程 BSM 遍历              →  GPU Batch (CuPy) + Streaming Agg   │
│  线性 Sticky-Strike           →  SABR / SVI 校准                    │
│  硬编码门控规则                →  Feature Store + ML Attention Fusion│
│  AgentA/B1/G 紧耦合           →  Signal Generators + Guard Rails     │
│  deepcopy JSON 广播            →  COW + Delta Encoding + Protobuf   │
│  三栏固定布局 React            →  Widget Compositor + WebGL + PWA    │
│  print 日志                    →  OpenTelemetry 全链路可观测         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 重构架构分层

```
┌─────────────────────────────────────────────────────────────────────┐
│                     L4 — 前端展示层                                  │
│  Widget Compositor · Zustand Store · WebGL/Canvas · PWA             │
│  Binary Protocol (Protobuf) · Command Palette (Ctrl+K)              │
│  Lightweight Charts · Responsive Panels · Custom Alerts             │
└─────────────────────────────┬───────────────────────────────────────┘
                               │  Protobuf binary / JSON (1Hz push)
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L3 — 输出组装层                                  │
│  PayloadAssembler (COW) · DeltaEncoder · Multi-Channel Distributor  │
│  Time-Series Store (Hot/Warm/Cold) · Presenter v2 (Pydantic)        │
│  Protobuf Schema · gRPC Stream · NATS/Kafka Event Bus               │
└─────────────────────────────┬───────────────────────────────────────┘
                               │  DecisionOutput + Audit Trail
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L2 — 决策分析层                                  │
│  Feature Store (Redis + Arrow) · Signal Generators (YAML config)    │
│  Attention Fusion (ML-Assisted) · Risk Guard Rails (Independent)    │
│  SHAP Explainer · Backtest Engine · Shadow Mode Deployment          │
└─────────────────────────────┬───────────────────────────────────────┘
                               │  EnrichedSnapshot (Arrow + Aggregates)
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L1 — 本地计算层                                  │
│  GPU Greeks Kernel (CuPy Batch) · Compute Router (GPU/Rust/Numba)  │
│  Streaming Aggregator (Incremental GEX) · SABR/SVI Calibration      │
│  Multi-freq VPIN (Rust SIMD) · L2 Depth BBO · Volume Entropy       │
└─────────────────────────────┬───────────────────────────────────────┘
                               │  Arrow RecordBatch (zero-copy)
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L0 — 数据摄取层                                  │
│  Rust IngestWorker (Tokio WS) · SanitizePipeline v2 (Stat Breaker) │
│  MVCC ChainStateStore · Adaptive Rate Governor · SPSC EventBus      │
│  Multi-Source Feed Abstraction · FPGA-Ready Interface               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 关键时序参数（重构后）

| 参数 | 当前值 | 目标值 | 说明 |
|------|--------|--------|------|
| `ingest_latency` | 5–15 ms | **< 1 ms** | Rust IngestWorker |
| `greeks_compute` | 30–80 ms | **< 5 ms** | GPU batch BSM |
| `decision_latency` | 50–200 ms | **< 20 ms** | Feature Store + ML Fusion |
| `assembly_latency` | 5–15 ms | **< 1 ms** | COW + Delta Encoding |
| `ws_broadcast` | 1s (固定) | 1s (可配置) | 背压感知 |
| `e2e_tick_to_render` | ~200–400 ms | **< 30 ms** | 全链路优化 |

---

## 层级文档索引

| 文档 | 层级 | 核心重构方向 |
|------|------|------------|
| [L0_DATA_FEED.md](./L0_DATA_FEED.md) | L0 | Event-First · Rust Ingest · MVCC · 统计断路器 |
| [L1_LOCAL_COMPUTATION.md](./L1_LOCAL_COMPUTATION.md) | L1 | GPU Batch BSM · 增量聚合 · SABR 校准 · 多频 VPIN |
| [L2_DECISION_ANALYSIS.md](./L2_DECISION_ANALYSIS.md) | L2 | Feature Store · ML Fusion · Guard Rails · XAI · 回测 |
| [L3_OUTPUT_ASSEMBLY.md](./L3_OUTPUT_ASSEMBLY.md) | L3 | COW 组装 · Delta 编码 · Protobuf · 多通道分发 · 时序存储 |
| [L4_FRONTEND.md](./L4_FRONTEND.md) | L4 | Binary Protocol · Zustand · WebGL · Widget · PWA |

---

## 总体迁移路线图

```
2025 Q3 ─────────────────────────────────────────────────────
  L0: SanitizePipeline 统计断路器 + OTel
  L1: CuPy GPU BSM batch + compute router
  L2: Feature Store 基础设施
  L3: Presenter 强类型化 (Pydantic)
  L4: Zustand state store

2025 Q4 ─────────────────────────────────────────────────────
  L0: Rust IngestWorker + SPSC EventBus
  L1: StreamingAggregator 增量聚合
  L2: Signal Generator 配置化 + Guard Rails
  L3: DeltaEncoder + Protobuf schema
  L4: Lightweight Charts + Canvas rendering

2026 Q1 ─────────────────────────────────────────────────────
  L0: MVCC ChainStateStore + Arrow 输出
  L1: SABR 校准 + 多频 VPIN + L2 depth BBO
  L2: Attention Fusion + Shadow Mode + SHAP
  L3: 多通道分发 (gRPC) + 三层时序存储
  L4: Protobuf binary WS + Widget compositor

2026 Q2 ─────────────────────────────────────────────────────
  L0: 多源 Feed 抽象 (Polygon/Databento)
  L1: Arrow RecordBatch 零拷贝交接
  L2: 回测框架 + Historical Feature Replay
  L3: Broadcast Governor + 背压感知
  L4: PWA 离线 + Command Palette

2026 H2 ─────────────────────────────────────────────────────
  L0: FPGA/Kernel Bypass 接口预留
  L1: SVI 校准 + fused Rust SIMD
  L2: Online A/B Testing + AutoML
  L3: Arrow Flight + Kafka/NATS
  L4: WebGL 渲染器 + Tauri 桌面版
```

---

## 原始文档归档

所有 v3 原始文档已备份至 `docs/backup/` 目录:

| 文件 | 大小 | 说明 |
|------|------|------|
| `backup/SYSTEM_OVERVIEW.md` | 7.6 KB | v3 架构总览 |
| `backup/L0_DATA_FEED.md` | 5.6 KB | v3 L0 数据摄取层 |
| `backup/L1_LOCAL_COMPUTATION.md` | 5.7 KB | v3 L1 本地计算层 |
| `backup/L2_DECISION_ANALYSIS.md` | 9.2 KB | v3 L2 决策分析层 |
| `backup/L3_OUTPUT_ASSEMBLY.md` | 6.8 KB | v3 L3 输出组装层 |
| `backup/L4_FRONTEND.md` | 8.0 KB | v3 L4 前端展示层 |

---

## 服务启动方式

```bash
# Backend (e:\US.market\Option_v3\backend)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend (e:\US.market\Option_v3\frontend)
npm run dev
```

默认访问: `http://localhost:5173`（前端） | `http://localhost:8001/health`（后端健康检查）

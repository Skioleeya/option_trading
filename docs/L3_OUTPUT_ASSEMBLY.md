# L3 — 输出组装层 (Output Assembly Layer)

## 2025–2026 主流金融架构重构指引

> **定位**: L3 是系统的发布中枢——将 L2 决策信号、L1 计算数据和 L0 原始快照组装为结构化 payload，通过高效协议分发给前端与外部消费者。
>
> **架构宗旨 (2025–2026)**: 从"Python dict 深拷贝 + JSON WebSocket 广播"模式，全面迁移至 **Protobuf/FlatBuffers 序列化 + 多通道分发 + 增量更新 (Delta Encoding) + Observability Dashboard Backend**。

---

## 1. 架构目标与度量标准

| KPI | 当前基线 (v3) | 2025 H2 目标 | 2026 目标 |
|-----|--------------|-------------|----------|
| Payload 组装延迟 | ~5–15 ms (deepcopy) | **< 1 ms** (结构化序列化) | **< 500 µs** (lazy COW) |
| WS 广播延迟 (100 客户端) | ~10–30 ms | **< 3 ms** | **< 1 ms** (binary protocol) |
| Payload 大小 | ~15–30 KB (JSON) | **< 5 KB** (Protobuf) | **< 2 KB** (delta encoding) |
| 广播可靠性 | best-effort | **at-least-once + 序列号** | exactly-once (ACK) |
| 历史查询延迟 (p99) | ~50–200 ms (Redis ZRANGEBYSCORE) | **< 20 ms** | **< 5 ms** (内存 Parquet) |

---

## 2. 输出架构 (Target State)

```
     L2 DecisionOutput + L1 EnrichedSnapshot + L0 Metadata
                           │
              ┌────────────▼────────────────┐
              │     L3 Assembly Reactor      │
              │                              │
              │  ┌──────────────────────┐    │
              │  │  Payload Assembler   │    │  ← COW 零拷贝组装
              │  │  (Structured Types)  │    │
              │  └──────────┬───────────┘    │
              │             │                │
              │  ┌──────────▼───────────┐    │
              │  │  Delta Encoder       │    │  ← 增量更新 (仅发送变化)
              │  │  (vs last payload)   │    │
              │  └──────────┬───────────┘    │
              │             │                │
              │  ┌──────────▼───────────┐    │
              │  │  Multi-Channel       │    │
              │  │  Distributor         │    │
              │  │  ├─ WS (binary PB)  │    │
              │  │  ├─ SSE (JSON)      │    │  ← 轻量级备选
              │  │  ├─ gRPC stream     │    │  ← 外部量化系统
              │  │  └─ Kafka/NATS      │    │  ← 微服务间通信
              │  └──────────┬───────────┘    │
              │             │                │
              │  ┌──────────▼───────────┐    │
              │  │  Time-Series Store   │    │  ← 内存 + 持久化
              │  │  (Arrow + Parquet)   │    │
              │  └──────────────────────┘    │
              │                              │
              └──────────────────────────────┘
```

---

## 3. Payload 组装 2.0

### 3.1 从 deepcopy 到 Copy-on-Write (COW)

当前问题：每次 compute tick 整个 payload 做 `deepcopy` → 大量 GC 压力。

```python
class PayloadAssembler:
    """Copy-on-Write 组装器 — 仅在变化时创建新引用"""

    def __init__(self):
        self._last_payload: FrozenPayload | None = None

    def assemble(self, decision: DecisionOutput,
                 snapshot: EnrichedSnapshot,
                 atm_decay: AtmDecayPayload) -> FrozenPayload:
        """组装不可变 payload"""

        # Presenters 仍然是纯函数
        ui_state = UIState(
            micro_stats=MicroStatsPresenter.build(decision),
            tactical_triad=TacticalTriadPresenter.build(decision),
            skew_dynamics=SkewDynamicsPresenter.build(decision),
            active_options=ActiveOptionsPresenter.build(snapshot),
            mtf_flow=MTFFlowPresenter.build(decision),
            wall_migration=WallMigrationPresenter.build(decision),
            depth_profile=DepthProfilePresenter.build(snapshot),
        )

        payload = FrozenPayload(
            timestamp=datetime.utcnow(),
            spot=snapshot.spot,
            signal=decision.signal,
            ui_state=ui_state,
            atm=atm_decay,
            version=snapshot.version,
        )

        self._last_payload = payload
        return payload
```

### 3.2 Presenter 2.0 — 强类型输出

从 dict 返回值迁移到 **Pydantic model / Protobuf message**:

```python
class MicroStatsOutput(BaseModel):
    """强类型 Presenter 输出"""
    net_gex: MetricCard
    wall_dynamics: MetricCard
    vanna_state: MetricCard
    momentum: MetricCard

class MetricCard(BaseModel):
    label: str
    value: str
    badge: str    # "positive" | "negative" | "neutral"
    tooltip: str  # 新增: 悬停解释
```

---

## 4. 增量更新 (Delta Encoding)

### 4.1 原理

大部分 ticker 之间，80%+ 的 payload 字段未变化。发送完整 JSON 是极大浪费。

### 4.2 实现方案

```python
class DeltaEncoder:
    """计算两次 payload 之间的差异"""

    def encode(self, current: FrozenPayload, previous: FrozenPayload | None) -> DeltaPayload:
        if previous is None:
            return DeltaPayload(type="full", data=current.to_dict())

        diff = {}
        for field in current.__fields__:
            curr_val = getattr(current, field)
            prev_val = getattr(previous, field)
            if curr_val != prev_val:
                diff[field] = curr_val

        return DeltaPayload(
            type="delta",
            version=current.version,
            prev_version=previous.version,
            changes=diff,
        )
```

```
客户端侧:
  if payload.type == "full":
      state = payload.data
  elif payload.type == "delta":
      assert state.version == payload.prev_version
      state = { **state, **payload.changes }
```

**带宽节省**: 预估 JSON 大小从 ~25 KB → ~3–5 KB (80% 压缩)。

---

## 5. 多通道分发架构

### 5.1 通道矩阵

| 通道 | 协议 | 格式 | 延迟 | 消费者 |
|------|------|------|------|--------|
| **Primary WS** | WebSocket | Protobuf (binary) | < 1 ms | React 仪表板 |
| **Legacy WS** | WebSocket | JSON | < 5 ms | 向后兼容 |
| **SSE Endpoint** | HTTP/2 SSE | JSON | < 10 ms | 移动端/轻量客户端 |
| **gRPC Stream** | gRPC bidirectional | Protobuf | < 1 ms | 外部量化系统 |
| **Event Bus** | NATS/Kafka | Protobuf | < 2 ms | 微服务下游消费 |

### 5.2 Protobuf Schema (核心)

```protobuf
syntax = "proto3";

message DashboardPayload {
  uint64 version = 1;
  google.protobuf.Timestamp timestamp = 2;
  double spot = 3;
  SignalData signal = 4;
  UIStateData ui_state = 5;
  AtmDecayData atm = 6;
}

message UIStateData {
  MicroStats micro_stats = 1;
  TacticalTriad tactical_triad = 2;
  SkewDynamics skew_dynamics = 3;
  repeated ActiveOption active_options = 4;
  MTFFlow mtf_flow = 5;
  repeated WallMigrationEntry wall_migration = 6;
  DepthProfile depth_profile = 7;
}

message MetricCard {
  string label = 1;
  string value = 2;
  string badge = 3;
  string tooltip = 4;
}
```

---

## 6. ATM Decay Tracker 2.0

| 改进 | 当前 | 目标 |
|------|------|------|
| 更新源 | chain + spot | **直接从 L1 EnrichedSnapshot** |
| 持久化 | Redis ZSET | **Redis TimeSeries + Parquet 日归档** |
| 历史查询 | 全日单序列 | **多 strike 追踪 + 比较** |
| 新指标 | IV + Theta | **+ Gamma acceleration + Realized vs Implied** |

---

## 7. 时序存储 2.0 (Time-Series Backend)

### 7.1 双层存储

```
┌─────────────────────────────────────────────────┐
│                Time-Series Store                 │
│                                                  │
│  Hot Layer (最近 2 小时):                        │
│    Arrow RecordBatch in-memory ring buffer       │
│    查询: O(1) 最新 N 条                          │
│                                                  │
│  Warm Layer (当日):                              │
│    Redis TimeSeries (per-field streams)           │
│    查询: 任意时间窗口聚合 (MRANGE)               │
│                                                  │
│  Cold Layer (历史):                              │
│    Parquet files on disk (daily rotation)         │
│    查询: DuckDB / Polars ad-hoc analysis         │
└─────────────────────────────────────────────────┘
```

### 7.2 API 端点升级

| 端点 | 当前 | 2025–2026 |
|------|------|---------|
| `GET /history` | Redis ZSET | Arrow Flight 或 REST + Protobuf |
| `GET /api/atm-decay/history` | Redis | Redis TimeSeries + 自动聚合 |
| `GET /api/features/history` | 无 | 新增: Feature Store 时序查询 |
| `GET /api/signals/history` | 无 | 新增: 信号审计日志查询 |
| `WebSocket /ws/dashboard` | JSON | Protobuf binary (向后兼容 JSON 备选) |

---

## 8. 双循环架构 2.0

```
_compute_reactor                     _broadcast_governor
  ├─ 从 L1 EventBus 消费快照         ├─ 固定 1Hz (可配置)
  ├─ L2 DecisionReactor.run()        ├─ DeltaEncoder.encode()
  ├─ PayloadAssembler.assemble()     ├─ 多通道分发 (WS + gRPC + NATS)
  ├─ TimeSeriesStore.write()         ├─ OTel span (broadcast_latency)
  └─ Event 发布到 internal bus       └─ 客户端 ACK 追踪 (可选)
```

**关键改进**:
- **Reactor 模式**: 计算循环从定时轮询改为事件驱动（L1 产出时立即触发）
- **Broadcast Governor**: 限速器确保高频计算不淹没客户端
- **背压感知**: 若客户端消费慢于 1Hz，自动降级为 delta-only 模式

---

## 9. 可观测性

| Span | 度量 |
|------|------|
| `l3.assemble` | 组装延迟、COW 命中率 |
| `l3.delta_encode` | 差异比例、压缩大小 |
| `l3.broadcast.ws` | per-client 延迟、消息积压 |
| `l3.broadcast.grpc` | stream 健康、重连次数 |
| `l3.timeseries.write` | 写入延迟、GC 频率 |
| `l3.presenter.*` | 各 Presenter 延迟 |

---

## 10. 迁移路线图

```
Phase 1 (2025 Q3): Presenter 强类型化 (Pydantic) + COW 组装
Phase 2 (2025 Q4): DeltaEncoder + Protobuf schema 定义
Phase 3 (2026 Q1): 多通道分发 (WS binary + gRPC)
Phase 4 (2026 Q1): Time-Series Store 三层架构
Phase 5 (2026 Q2): Broadcast Governor + 背压感知
Phase 6 (2026 H2): Arrow Flight 历史查询 + Kafka/NATS 事件总线
```

---

## 11. 关键文件（当前 → 目标映射）

| 当前文件 | 重构目标 | 备注 |
|---------|---------|------|
| `services/system/snapshot_builder.py` | → `assembly/payload_assembler.py` | COW + 强类型 |
| `ui/*.py` (7 Presenters) | → `presenters/*.py` (Pydantic output) | 输出类型化 |
| `services/system/historical_store.py` | → `storage/timeseries_store.py` | 三层存储 |
| `services/system/redis_service.py` | 保持 + 增加 TimeSeries 支持 | — |
| `main.py` (AppContainer) | → `runtime/compute_reactor.py` + `runtime/broadcast_governor.py` | 分离 |
| — (新文件) | `assembly/delta_encoder.py` | 增量编码 |
| — (新文件) | `proto/dashboard.proto` | Protobuf 定义 |
| — (新文件) | `channels/grpc_server.py` | gRPC 流式端点 |
| — (新文件) | `channels/nats_publisher.py` | 事件总线 |

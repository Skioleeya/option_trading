# L3 — 输出组装层 (Output Assembly Layer)

> **定位**: L3 是系统的发布中枢——负责消费 L2 决策信号、L1 量化计算快照以及 L0 元数据，将其高效打包为全量/增量 Payload 结构，再通过广播轮询器向前端 WebSocket 客户端安全推送。
>
> **架构状态 (v3.1)**: 已摒弃落后的 `SnapshotBuilder` (Python 字典深拷贝满天飞)，完全迁移至 **"Write-on-Copy (COW) Assembler + 强类型 Pydantic Presenters + Delta Encoder 增量编码 + 并发 Governor"**。

---

## 1. 核心输出架构 (当前状态)

```
      L2 DecisionOutput + L1 EnrichedSnapshot + AtmDecay
                           │
              ┌────────────▼────────────────┐
              │     L3AssemblyReactor       │
              │                             │
              │  ┌───────────────────────┐  │
              │  │  PayloadAssemblerV2   │  │ ← COW 组装器，双源兼容
              │  │  (Frozen Dataclass)   │  │
              │  └──────────┬────────────┘  │
              │             │               │
              │  ┌──────────▼────────────┐  │ ← UI State Presenters 子集
              │  │ TacticalTriadPresenter│  │   MicroStats / ActiveOptions
              │  │ WallMigrationPresenter│  │   MTFFlow / SkewDynamics
              │  │ DepthProfilePresenter │  │   [使用 Numba/GPU 路由处理海量数据]
              │  └──────────┬────────────┘  │
              │             │               │
              │  ┌──────────▼────────────┐  │
              │  │  FieldDeltaEncoder    │  │ ← 增量提取：仅下发 Diff 结构
              │  │  (vs last payload)    │  │
              │  └──────────┬────────────┘  │
              │             │               │
              │  ┌──────────▼────────────┐  │
              │  │ BroadcastGovernor     │  │ ← Asyncio.gather 并发推送
              │  └──────────┬────────────┘  │
              │             │               │
              └─────────────┼───────────────┘
                            │
               WebSocket / HTTP Client (L4)
```

## 2. 写时复制组装 (PayloadAssembler & Target COW)

- **废除 Deepcopy**：新的 `FrozenPayload` 对全链路不可变 (Immutable)。各模块状态组装利用引用传递（尤其是 `active_options` 这种超大会话结构）；一旦生成不可篡改。
- **兼容模式接回**：提供 `to_dict()` 完美对齐老版本 `agent_g.data.*` 的扁平化 JSON Schema，保证 L4 终端无痛切换。同时实现了深层解包逻辑，针对性地提取 `AgentResult.data["fused_signal"]` 旁路传导到前端，避开了以往对字典嵌套丢字段的问题。
- **异常短路/清零机制**：内部包裹了健壮的 Error Path，一旦某微结构遭遇 NaN 生成错误，返回 `neutral/zero-state` 而非把错误数据推到前台。

## 3. 分化重构：Presenters V2

负责把 L1/L2 的裸数据“梳妆打扮”为前台使用的 UI 部件（MetricCard 等）：
- **DepthProfilePresenterV2**：最为复杂，接收 100 档全链 Greeks 数据。内嵌 EMA 2-Tier 收敛系统计算 Gamma Profile。利用 `STRIKE_COUNT` (14 档) 窗口进行裁剪平滑，阻断 NaN/Inf 无效数据。
- **其它 Presenters**：含 `MicroStats`, `TacticalTriad`, `WallMigration`, `MTFFlow` 等，负责封装 Badge/Tooltip 元信息供 UI 组件渲染。

## 4. 增量更新 (Field Delta Encoding)

为了避免 1 Hz 高频广播对 WebSocket 带宽的摧残引发堵塞（尤其是客户端背压引起后端 OOM）：
- 只要上游 Snapshot 发生计算循环，`BroadcastGovernor` 会使用 `FieldDeltaEncoder` 同 `_last_payload` 比对。
- 如果数据没有突变（例如周末停盘、夜盘断流），生成并推送轻量级 Keepalive / Delta Payload。
- 设计上附带 30s 的强制全量快照 (Full Flush) 防错纠偏机制。

## 5. 多层时序存储 (Time-Series Store)

不仅向外推热数据，还要兼顾历史查阅（供 UI 绘制 K 线）：
- **Hot Layer (内存)**：采用 `collections.deque` 实现 O(1) 最近数据读取。
- **Warm Layer (Redis)**：自动转码写入 Redis TimeSeries，向后兼容原先的 `/history` 和 `/api/atm-decay/history` 接口请求。

## 6. 迁移与升级路线图 (2025-2026 Vision)

- **Phase 1 (v3.1，已完成)**：写时复制组装器 + Presenter 强类型化 + Delta 增量压缩 + Asyncio 并行广播。
- **Phase 2 (2025 Q4)**：Protobuf (PB) / Flatbuffers 极简二进制序列化，彻底终结 JSON。
- **Phase 3 (2026 Q1)**：gRPC 双向流 API 通道接入（针对外部机构量化引擎消费）。
- **Phase 4 (2026 H2)**：Cold Layer 落盘引擎（Arrow Flight / DuckDB 加速 Parquet 历史离线分析引擎）。

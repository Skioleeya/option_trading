# L3 — 输出组装层 (Output Assembly Layer)

> **定位**: L3 是系统的发布中枢——负责消费 L2 决策信号、L1 量化计算快照以及 L0 元数据，将其高效打包为全量/增量 Payload 结构，再通过广播轮询器向前端 WebSocket 客户端安全推送。
>
> **架构状态 (v4.0)**: 已升级为**威胁敏感型组装器 (Threat-Aware Assembler)**。`ActiveOptionsPresenter` 现在由绝对威胁指数 (OFII) 驱动排序，并为扫单行自动注入 `is_sweep` 物理视觉标识。

---

## 1. 核心输出架构 (当前状态)

```
      L2 DecisionOutput + L1 EnrichedSnapshot + AtmDecay
                           │
              ┌────────────▼────────────────┐
              │     L3AssemblyReactor       │
              │                             │
              │  ┌───────────────────────┐  │
              │  │  PayloadAssemblerV2   │  │ ← COW 组装器，数据源聚合
              │  │  (Frozen Dataclass)   │  │
              │  └──────────┬────────────┘  │
              │             │               │
              │  ┌──────────▼────────────┐  │ ← UI State Engine (单源提取)
              │  │    UIStateTracker     │  │   [Consolidates Microstructure]
              │  └──────────┬────────────┘  │
              │             │               │
              │  ┌──────────▼────────────┐  │ ← UI State Presenters 子集
              │  │ TacticalTriadPresenter│  │   MicroStats / ActiveOptions
              │  │ WallMigrationPresenter│  │   MTFFlow / SkewDynamics
              │  │ DepthProfilePresenter │  │   [使用 Numba/GPU 路由处理数据]
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

## 2. 写时复制组装 (PayloadAssembler V2)

- **写时复制组装 (COW Assembler)**：已升级为 `PayloadAssemblerV2`，支持双向解包（L1 `EnrichedSnapshot` 与 L0 Legacy Dict）。
- **元数据智能提取**：组装器现具备显式提取 `EnrichedSnapshot.extra_metadata` 的能力。这保证了 L0 生产的诊断信号（如 `rust_active`, `shm_stats`）能无缝进入 `FrozenPayload` 广播路径。
- **废除 Deepcopy**：新的 `FrozenPayload` 对全链路不可变 (Immutable)。各模块状态组装利用引用传递（尤其是 `active_options` 这种超大会话结构）；一旦生成不可篡改。
- **兼容模式与扁平化设计**：提供 `to_dict()` 完美对齐老版本 `agent_g.data.*` 的 JSON Schema，同时在顶层注入 `rust_active` 状态位用于前端健康指示灯，保证 L4 终端无痛切换。
- **微结构状态聚合**：由 `UIStateTracker` 直接从 L1 `EnrichedSnapshot` 提取并聚合所有微观信号（IV Velocity, Wall Migration, Vanna Flow 等），确保了 L3 广播负载的 100% 数据完整性。

### 2.2 IPC 诊断元数据契约 (2026-03-06)

- **字段完整性**：L3 透传到 L4 的 `shm_stats` 至少包含 `status`, `head`, `tail` 三个键；缺失任一关键键会削弱 DebugOverlay 的堵塞诊断能力。
- **类型约束**：`head/tail` 应保持数值或可安全转数值的字符串；`status` 应为稳定短字符串（如 `OK`, `DISCONNECTED`）。
- **回退语义**：当 `shm_stats` 不可用时，L4 可回退读取 `rust_active` 显示 ONLINE/DISCONNECTED，但该回退仅用于可视化兜底，不替代 L3 正常透传职责。

### 2.3 ATM IV 字段透传契约 (2026-03-06 Hotfix)
- **字段命名桥接**：L1/L3 内部使用 `atm_iv`，对前端输出必须桥接为 `agent_g.data.spy_atm_iv`。
- **来源一致性**：`spy_atm_iv` 必须来自当前 `EnrichedSnapshot.atm_iv`，不得缓存旧帧值或降级为静态默认值。
- **版本一致性前提**：上游 `EnrichedSnapshot.version` 必须真实递增，确保 `spy_atm_iv` 对应当前快照而非 TTL 残留。

### 2.4 数据时间戳与广播时间戳契约 (2026-03-06 P0 Debt Fix)
- **`data_timestamp/timestamp`**：必须绑定 L0 源时间戳（`source_data_timestamp_utc`），禁止回退为 L1/L2 计算完成时间作为默认主路径。
- **`broadcast_timestamp/heartbeat_timestamp`**：仅表示 L3 广播时刻（UTC ISO8601），用于链路存活与时效诊断。
- **drift 语义**：`drift_ms` 统一定义为 `L2 computed_at - L0 source_data_timestamp_utc`。

### 2.5 TacticalTriad 阈值与状态透传契约 (2026-03-06 Hotfix)
- **VRP 基线单位守卫**：`vrp_baseline_hv` 若以小数形式误入（`<= 1.0`），必须在组装链路按百分比解释（`x100`）后再参与 `VRP = ATM_IV% - baseline_hv%`。
- **S-VOL 状态保真**：`DANGER_ZONE / GRIND_STABLE / VANNA_FLIP / UNAVAILABLE` 必须完整透传到 `ui_state.tactical_triad.svol_state`，禁止折叠为单一 `NORMAL`。
- **缺失值语义**：当相关性缺失或不可计算时，`svol_corr` 必须为 `null`，并将 `svol_state` 标记为 `UNAVAILABLE`，避免伪造 `0.00 STBL`。

### 2.6 SkewDynamics 状态契约 (2026-03-06 Hotfix)
- **输入来源唯一**：`UIStateTracker` 只从 `decision.feature_vector.skew_25d_normalized` 读取 skew 值，不从前端或 presenter 反推。
- **阈值判定**：`skew < skew_speculative_max => SPECULATIVE`，`skew > skew_defensive_min => DEFENSIVE`，其余为 `NEUTRAL`。
- **稳定回退**：`SkewDynamicsPresenterV2` 在空输入/异常时必须返回完整 `NEUTRAL` 结构，不得返回空字典 `{}`。
- **色彩语义**：延续亚洲盘语义，`SPECULATIVE -> 红`，`DEFENSIVE -> 绿`，`NEUTRAL -> theme neutral`。

### 2.7 ActiveOptions 字段保真契约 (2026-03-06 Hotfix)
- **字段不可丢失**：`ActiveOptionRow`/`ui_state.active_options[*]` 必须保留 `impact_index` 与 `is_sweep`，禁止在 typed adapter/serializer 阶段被截断。
- **类型归一化**：`option_type` 在 L3 输出必须归一化为 `CALL|PUT`；允许输入兼容 `C|P`，但不得原样透传到 L4。
- **排序语义保真**：L3 保持后台 Presenter 输出顺序（已按 `impact_index` 排序），前端不得在无明确策略时重排。

### 2.8 MTF 共识源一致性契约 (2026-03-06 Hotfix)
- **单一优先源**：`UIStateTracker` 生成 `ui_state.mtf_flow` 时，必须优先采用 L1 `snapshot.microstructure.mtf_consensus`，禁止无条件本地重算覆盖。
- **回退策略**：仅当 L1 `mtf_consensus` 缺失或结构非法时，才允许回退到 L3 本地 `MTFIVEngine` 估算值。
- **一致性目标**：L2 决策使用的 `mtf_consensus` 与 L4 `MtfFlow` 展示语义必须同源，避免“信号看涨但面板中性”的跨层漂移。

### 2.9 防耦合边界契约 (2026-03-06 Guardrail)
- **L2 契约导入白名单**：L3 允许导入 `l2_decision.events/*` 契约；禁止导入 `l2_decision.signals/*`、`l2_decision.agents/*` 等实现模块。
- **Presenter 纯度要求**：`l3_assembly/presenters/ui/*` 禁止直接导入 `l1_compute.analysis/*` 与 `l1_compute.trackers/*`；输入必须来自 `EnrichedSnapshot` 或组装层注入参数。
- **前端边界**：L3 禁止导入 `l4_ui/*`（包括类型或实现），L4 只通过协议负载消费 L3。
- **校验方式**：上述规则由 `scripts/policy/layer_boundary_rules.json` 提供，`validate_session.ps1 -Strict` 命中即失败。

### 2.1 MicroStats 状态契约补丁 (2026-03-06)

- **`wall_dyn` 强制映射**：`PayloadAssemblerV2` 必须将 `ui_metrics.wall_migration_data` 归一化后显式映射为 `micro_stats.wall_dyn` 输入，禁止遗漏该桥接步骤。
- **极端状态不可吞噬**：`BREACHED / DECAYING / UNAVAILABLE` 不得被降级为 `STABLE`。L3 必须保持原始风险语义到前端。
- **Badge Token 保真**：L3 `MetricCard.badge` 白名单已扩展到前端真实使用集合（含 `badge-red / badge-purple / badge-hollow-green / badge-red-dim` 等），避免语义颜色在序列化阶段被“中性化”。

## 3. 分化重构：Presenters V2

负责把 L1/L2 的裸数据“梳妆打扮”为前台使用的 UI 部件（MetricCard 等）：
- **DepthProfilePresenterV2**：最为复杂，接收 100 档全链 Greeks 数据。内嵌 EMA 2-Tier 收敛系统计算 Gamma Profile。利用 `STRIKE_COUNT` (14 档) 窗口进行裁剪平滑，阻断 NaN/Inf 无效数据。
- **ActiveOptionsPresenter (v4.0 演进)**：全面采用 OFII 作为顶层排序权重。负责为前端生成包含 `impact_index` 和 `is_sweep` 字段的 UI 负载。实现跨行数据横向对比，将“最高绝对威胁”置顶，而非单纯的成交量。
- **其它 Presenters**：含 `MicroStats`, `TacticalTriad`, `WallMigration`, `MTFFlow` 等。

### 3.1 MicroStats 模块边界 (2026-03-06)

- **状态机模块化**：`MicroStats` 的墙体复合态判定已拆分为独立模块（`wall_dynamics`），`presenter` 仅负责去抖与封装，禁止在渲染映射层混入判定逻辑。
- **Urgent 状态直通**：`BREACH` 为一级风险状态，必须绕过去抖延迟，首 Tick 即提交。
- **去抖仅用于常规态**：`PINCH / SIEGE / RETREAT / COLLAPSE / STABLE` 仍执行去抖，避免单 Tick 抖动造成徽标闪烁。

## 4. 增量更新 (Field Delta Encoding)

为了避免 1 Hz 高频广播对 WebSocket 带宽的摧残引发堵塞（尤其是客户端背压引起后端 OOM）：
- 只要上游 Snapshot 发生计算循环，`BroadcastGovernor` 会使用 `FieldDeltaEncoder` 同 `_last_payload` 比对。
- **1Hz 实时同步与 `agent_g_data` 嵌套**：针对全量/增量负载不匹配问题，已将 `net_gex`, `gamma_walls`, `gamma_flip_level`, `atm_iv` 聚合在 `agent_g_data` 容器下。`FieldDeltaEncoder` 现在能正确识别并下发这些顶层字段的差异。
- **视觉阈值裁剪 (Visual Thresholding)**：根据 2025 量化前端标准，delta 更新时仅下发离现价 (Spot) ±5% 以内的行，以及关键“英雄 Strike”（如 Flip Level, Walls）。此举将增量数据量压低了 93%。
- **精度强制归约 (Precision Rounding)**：所有浮点数值在 L3 序列化阶段强制执行 `round(x, 4)`，极大降低了 JSON 序列化和浏览器主线程解析的长尾开销。
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

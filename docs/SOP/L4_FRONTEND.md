# L4 — 前端展示层 (Frontend Presentation Layer)

> **定位**: L4 是系统的人机界面——将 L3 组装的结构化数据以极低延迟渲染到浏览器前端，支持机构级交易员的实时分析、决策和状态追踪。
>
> **架构状态 (v4.0)**: 已实现**机构级视觉同步 (Institutional Visualization Sync)**。`ActiveOptions` 组件新增 `IMP` (Impact) 列，并针对检测到的机构扫单 (Sweeps) 应用了高频呼吸脉冲动画与外发光特效。

---

## 1. 核心前端架构 (当前状态)

```
              L3 Multi-Channel Output (WebSocket JSON)
                       │
          ┌────────────▼────────────────┐
          │     L4 Frontend Runtime     │
          │                             │
          │  ┌──────────────────────┐   │
          │  │  Protocol Adapter    │   │ ← WS 连接管理、指数退避重连
          │  │  (JSON / Deltas)     │   │
          │  └──────────┬───────────┘   │
          │             │               │
          │  ┌──────────▼───────────┐   │
          │  │  Connection Monitor  │   │ ← 5态连接机: RUNNING, STALLED...
          │  └──────────┬───────────┘   │
          │             │               │
          │  ┌──────────▼───────────┐   │
          │  │  Delta Decoder       │   │ ← JSON-Patch (RFC 6902) 就地热更新
          │  └──────────┬───────────┘   │
          │             │               │
          │  ┌──────────▼───────────┐   │
          │  │  DashboardStore      │   │ ← Zustand + Immer (Immutable)
          │  │  (subscribeWith... ) │   │   支持深拷贝阻断与 Sticky-Key
          │  └──────────┬───────────┘   │
          │             │               │
          │  ┌──────────▼───────────┐   │ ← 12个自治面板组件
          │  │  12 Autonomous       │   │   直接从 Store Selector 取数据
          │  │  React Components    │   │   (取代祖父节点 Prop Drilling)
          │  └──────────┬───────────┘   │
          │             │               │
          │  ┌──────────▼───────────┐   │
          │  │  L4Rum / AlertEngine │   │ ← 性能遥测 API 与内部状态机告警
          │  └──────────────────────┘   │
          └─────────────────────────────┘
```

## 2. 状态管理与差分合并 (Zustand + JSON-Patch)

### 2.1 抛弃全树渲染
老版本因为顶层接收 `payload` 导致 React 发生 DOM 全量 Diff `(O(N))`，现在通过 `subscribeWithSelector` 将 12个视图组件剥离：
- 每个组件利用 `useDashboardStore(state => state.specific_field)` 获取唯一关心的数据。
- **行级记忆化 (Row-Level Memoization)**：`DepthProfile` 组件已重构为原子行模式。利用自定义 `React.memo` 比较函数，只有当特定 Strike 的数据发生位移时才重新渲染 DOM，极大地降低了 224 行长列表的 Reconciliation 成本。
- **保护性 Sticky Keys**：在 WS 不慎推送缺失（None）如 `ui_state` 时，Store 会锁住上一帧旧数据以防止白屏闪烁。

### 2.2 协议管道解耦 (Protocol / Delta decoupling)
- 通信层：由于引入 `FieldDeltaEncoder`，前端专门提取了 `DeltaDecoder`，基于开源 `fast-json-patch` 进行变更树合并。
- **历史记录精简 (History Pruning)**：`atmHistory` 环形缓冲区上限从 50,000 压降至 5,000。解决了连接波动时由于全量同步 5万点导致的 $O(N)$ 渲染卡死问题。
- **可见性守护 (Visibility Guard)**：`AtmDecayChart` 引入了 `document.visibilityState` 监听。当标签页处于后台时，自动暂停昂贵的 Canvas 绘制和 Canvas 数据构建，节省至少 15% 的闲置 CPU。
- 只有触发 `patch` 才执行状态树写操作。

### 2.4 时间戳消费契约 (2026-03-06 P0 Debt Fix)
- 前端 `payload.timestamp`（及 `data_timestamp`）语义统一为 **L0 源数据 UTC 时间**，不得解释为本地渲染时间或广播时间。
- `heartbeat_timestamp` 保持广播心跳语义，用于连接健康与时效显示。
- 展示层继续按 `America/New_York` 渲染，不改变视觉行为，只明确数据时间来源。

### 2.5 P1 命令导航与 ATM 图增量渲染契约 (2026-03-06)
- **命令导航闭环**：`CommandRegistry` 派发的 `l4:nav_spot|l4:nav_call_wall|l4:nav_put_wall|l4:nav_flip` 必须由 `DepthProfile` 监听并执行滚动。
- **回退策略**：目标 strike 不存在时，必须采用最近 strike 回退（nearest fallback），禁止静默无响应。
- **渲染增量优先**：`AtmDecayChart` 正常 append 路径使用 `series.update(...)`，仅在历史回灌/重排/非前缀更新时回退全量 `setData(...)`。
- **无行为回归**：保持现有显示模式切换、marker 逻辑与页面不可见时的绘制保护不变。

## 3. UI 微组件及面板

UI 在保持原版 TradingView-style 的冷酷暗色调三栏版式同时（`lib/theme.ts` 标准化管理设计 Tokens），内部划分如下：

- **左栏**：微观结构 (`MicroStats`), Gamma/Vanna 流动变局 (`WallMigration`), 全链横向扫描引擎 (`DepthProfile`)
- **中栏**：高频行情 Head (`Header`), Gex绝对值条 (`GexStatusBar`), ATM 衰减动能 (`AtmDecayChart` / `Overlay`)
- **右栏**：多重决策融合器 (`DecisionEngine`), 核心博弈极向 (`TacticalTriad`), Skew 曲率 (`SkewDynamics`), 资金流 (`MtfFlow`), 活跃榜 (`ActiveOptions` - **v4.0 增强**: 支持 Impact 排序与 Sweep 呼吸灯)
- **隐藏诊断面 (v3.1)**: 引入了名为 **Hack Matrix** 的底层 L1 SIMD 数据诊断大屏（`DebugOverlay.tsx`），通过 `Ctrl+D` 热键或 `CommandPalette` (`Ctrl+K`) 唤出，供量化研究员核对底层算力。另外 `DecisionEngine` 组件内也会将微观值以 `[7px]` 极小字体暗化挂载展示（注：严格使用 `??` 和 `!== undefined` 来确保合法空值 `0.0` 正确渲染，防止被 JS 弱类型逻辑隐藏）。

### 3.3 DebugOverlay / CommandPalette 热修契约 (2026-03-06)

- **全局热键契约**：`Ctrl/Cmd + D` 必须在运行时直接触发 `l4:toggle_debug_overlay` 事件（DEV 模式），不能仅停留在命令面板文案或命令项定义。
- **Hook 顺序安全**：`DebugOverlay` 中所有 Hooks（含 `useMemo`）必须在任何早返回（`if (!open) return null`）之前调用，禁止条件化 Hook，避免 React Hook 顺序错误。
- **诊断字段契约**：`DebugOverlay` 必须消费 `payload.shm_stats.status/head/tail` 并派生 `head-tail`，用于 IPC 堵塞排查；`shm_stats` 缺失时可回退到 `rust_active` 推断状态。
- **模块边界**：搜索、热键、诊断数据归一化应拆为独立模块（`commandPaletteSearch`、`commandPaletteHotkeys`、`debugOverlayModel`），组件层仅负责展示与事件绑定。

### 3.1 WallMigration 颜色与状态治理 (2026-03-06)
- **Token 单一来源**：`WallMigration` 必须通过专用主题模块统一管理颜色/边框/阴影 token，禁止组件内散落硬编码状态色。
- **亚洲风格一致性**：严格执行 `红涨绿跌`（Call/上涨=Red，Put/下行=Green），并与 `theme.ts`/`index.css` 变量保持一致。
- **后端灯光透传优先**：`row.lights.current_*` 作为视觉主信号优先级高于本地 fallback，防止 L3→L4 状态语义偏移。
- **健壮解析**：状态字符串与历史值渲染需容错（空值/非数值不崩溃），确保 WS 短暂缺帧时组件稳定。

### 3.2 MicroStats 状态与配色契约 (2026-03-06)

- **四卡数据源唯一**：`MicroStats` 仅从 `ui_state.micro_stats.{net_gex, wall_dyn, momentum, vanna}` 取值；L4 不自行重算状态。
- **风险态直达显示**：当 `wall_dyn.label=BREACH/DECAY/WARM↑` 时，前端必须原样渲染，不允许本地 fallback 覆盖为 `STABLE`。
- **亚洲风格语义保持**：
  - `MOMENTUM`: `BULLISH -> LONG -> 红`, `BEARISH -> SHORT -> 绿`
  - `WALL DYN`: `RETREAT -> 红`, `COLLAPSE -> 绿`, `PINCH -> 紫`, `BREACH -> 琥珀`
  - `VANNA`: `DANGER -> 红`, `CMPRS -> 青色空心`, `FLIP -> 紫`
- **Store 合并注意事项**：`micro_stats` 当前非 sticky key。若后端发送空对象，组件会回退 `—`。运维需优先确保 L3 持续输出完整 `micro_stats`。
## 4. 连接守护与告警系统 (Monitor & Alerts)

- **ConnectionMonitor**: 接管 WS 心跳。实现状态五连跳 `DISCONNECTED → CONNECTING → AWAIT_STATE → RUNNING → STALLED`。
- **RDS 黄灯修复契约（2026-03-06）**：`ProtocolAdapter` 必须在每条有效文本帧（`dashboard_update/dashboard_init/dashboard_delta/keepalive`）到达时调用 `ConnectionMonitor.onKeepalive()`，禁止只依赖后端 30s keepalive，避免 3s stall 阈值导致误报 `RDS STALLED`。
- **健康判定语义**：`RDS STALLED` 仅表示心跳超时，不等同于 WS 断连；若数据帧持续到达则应保持 `RDS LIVE`。
- **后端健康指示灯**: L4 `Header` 组件利用 `rust_active` 状态位实时展示 **Rust Ingest Gateway** 是否在线。
- **IPC 深度诊断**: `DebugOverlay` 现在能够解析并展现共享内存的读写指针 (Head/Tail) 差值，供极端场景下的延迟排查。
- **前后端排障边界**: 若出现 Hook 顺序报错（如 `Rendered more hooks than during the previous render`），属于 L4 前端渲染错误，不应通过重启后端解决；优先重启前端 dev server 并检查组件 Hook 调用顺序。
- **AlertEngine**: 纯粹由状态发生位移被动触发。实现了：信号方向翻转防抖告警、GEX 面板正负穿越警告、Spot 刺穿 Call/Put Wall 致命警报。配备 `cooldown` 冷却防打扰。
- **前端可观测 (L4Rum)**：使用浏览器原生的 `Performance API` 记录首字节至挂载延迟，帧率跌落以及堆内存快照。

## 5. 迁移与升级路线图 (2025-2026 Vision)

- **Phase 1 (v3.1，已完成)**：协议与状态解耦 / Zustand 渲染截断 / 12组件自治化 / L4Rum。
- **Phase 2 (2025 Q4)**：WebGL 替代 React SVG (`DepthProfile`)；引入极高性能图表库 `Lightweight Charts`。
- **Phase 3 (2026 Q1)**：二进制 `Protobuf` + `ArrayBuffer` 解码，进一步将 payload 切割至 2KB 以内。
- **Phase 4 (2026 H2)**：`WidgetCompositor` 拖拽与可拆分多面屏，支持多监视器 PWA。

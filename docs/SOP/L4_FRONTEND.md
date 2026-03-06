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

## 3. UI 微组件及面板

UI 在保持原版 TradingView-style 的冷酷暗色调三栏版式同时（`lib/theme.ts` 标准化管理设计 Tokens），内部划分如下：

- **左栏**：微观结构 (`MicroStats`), Gamma/Vanna 流动变局 (`WallMigration`), 全链横向扫描引擎 (`DepthProfile`)
- **中栏**：高频行情 Head (`Header`), Gex绝对值条 (`GexStatusBar`), ATM 衰减动能 (`AtmDecayChart` / `Overlay`)
- **右栏**：多重决策融合器 (`DecisionEngine`), 核心博弈极向 (`TacticalTriad`), Skew 曲率 (`SkewDynamics`), 资金流 (`MtfFlow`), 活跃榜 (`ActiveOptions` - **v4.0 增强**: 支持 Impact 排序与 Sweep 呼吸灯)
- **隐藏诊断面 (v3.1)**: 引入了名为 **Hack Matrix** 的底层 L1 SIMD 数据诊断大屏（`DebugOverlay.tsx`），通过 `Ctrl+D` 热键或 `CommandPalette` (`Ctrl+K`) 唤出，供量化研究员核对底层算力。另外 `DecisionEngine` 组件内也会将微观值以 `[7px]` 极小字体暗化挂载展示（注：严格使用 `??` 和 `!== undefined` 来确保合法空值 `0.0` 正确渲染，防止被 JS 弱类型逻辑隐藏）。
## 4. 连接守护与告警系统 (Monitor & Alerts)

- **ConnectionMonitor**: 接管 WS 心跳。实现状态五连跳 `DISCONNECTED → CONNECTING → AWAIT_STATE → RUNNING → STALLED`。
- **后端健康指示灯**: L4 `Header` 组件利用 `rust_active` 状态位实时展示 **Rust Ingest Gateway** 是否在线。
- **IPC 深度诊断**: `DebugOverlay` 现在能够解析并展现共享内存的读写指针 (Head/Tail) 差值，供极端场景下的延迟排查。
- **AlertEngine**: 纯粹由状态发生位移被动触发。实现了：信号方向翻转防抖告警、GEX 面板正负穿越警告、Spot 刺穿 Call/Put Wall 致命警报。配备 `cooldown` 冷却防打扰。
- **前端可观测 (L4Rum)**：使用浏览器原生的 `Performance API` 记录首字节至挂载延迟，帧率跌落以及堆内存快照。

## 5. 迁移与升级路线图 (2025-2026 Vision)

- **Phase 1 (v3.1，已完成)**：协议与状态解耦 / Zustand 渲染截断 / 12组件自治化 / L4Rum。
- **Phase 2 (2025 Q4)**：WebGL 替代 React SVG (`DepthProfile`)；引入极高性能图表库 `Lightweight Charts`。
- **Phase 3 (2026 Q1)**：二进制 `Protobuf` + `ArrayBuffer` 解码，进一步将 payload 切割至 2KB 以内。
- **Phase 4 (2026 H2)**：`WidgetCompositor` 拖拽与可拆分多面屏，支持多监视器 PWA。

# L4 — 前端展示层 (Frontend Presentation Layer)

> **定位**: L4 是系统的人机界面——将 L3 组装的结构化数据以极低延迟渲染到浏览器前端，支持机构级交易员的实时分析、决策和状态追踪。
>
> **架构状态 (v3.1)**: 已完成从杂乱的 Prop Drilling 模式向 **"Zustand 不可变状态树 + 精确订阅 (Selector) + 纯协议分离适配器"** 的整体重构。代码库完全迁移至全新的 `l4_ui/` 目录。

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
- 利用 `React.memo` 作为防洪堤，阻断非自身数据的任何多余 Rerender。
- **保护性 Sticky Keys**：在 WS 不慎推送缺失（None）如 `ui_state` 时，Store 会锁住上一帧旧数据以防止白屏闪烁。

### 2.2 协议管道解耦 (Protocol / Delta decoupling)
- 通信层：由于引入 `FieldDeltaEncoder`，前端专门提取了 `DeltaDecoder`，基于开源 `fast-json-patch` 进行变更树合并。
- 只有触发 `patch` 才执行状态树写操作。

## 3. UI 微组件及面板

UI 在保持原版 TradingView-style 的冷酷暗色调三栏版式同时（`lib/theme.ts` 标准化管理设计 Tokens），内部划分如下：

- **左栏**：微观结构 (`MicroStats`), Gamma/Vanna 流动变局 (`WallMigration`), 全链横向扫描引擎 (`DepthProfile`)
- **中栏**：高频行情 Head (`Header`), Gex绝对值条 (`GexStatusBar`), ATM 衰减动能 (`AtmDecayChart` / `Overlay`)
- **右栏**：多重决策融合器 (`DecisionEngine`), 核心博弈极向 (`TacticalTriad`), Skew 曲率 (`SkewDynamics`), 资金流 (`MtfFlow`), 活跃榜 (`ActiveOptions`)

## 4. 连接守护与告警系统 (Monitor & Alerts)

- **ConnectionMonitor**: 接管 WS 心跳。实现状态五连跳 `DISCONNECTED → CONNECTING → AWAIT_STATE → RUNNING → STALLED`。
- **AlertEngine**: 纯粹由状态发生位移被动触发。实现了：信号方向翻转防抖告警、GEX 面板正负穿越警告、Spot 刺穿 Call/Put Wall 致命警报。配备 `cooldown` 冷却防打扰。
- **前端可观测 (L4Rum)**：使用浏览器原生的 `Performance API` 记录首字节至挂载延迟，帧率跌落以及堆内存快照。

## 5. 迁移与升级路线图 (2025-2026 Vision)

- **Phase 1 (v3.1，已完成)**：协议与状态解耦 / Zustand 渲染截断 / 12组件自治化 / L4Rum。
- **Phase 2 (2025 Q4)**：WebGL 替代 React SVG (`DepthProfile`)；引入极高性能图表库 `Lightweight Charts`。
- **Phase 3 (2026 Q1)**：二进制 `Protobuf` + `ArrayBuffer` 解码，进一步将 payload 切割至 2KB 以内。
- **Phase 4 (2026 H2)**：`WidgetCompositor` 拖拽与可拆分多面屏，支持多监视器 PWA。

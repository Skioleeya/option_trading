# L4 — 前端展示层 (Frontend Presentation Layer)

> **职责**: React + TypeScript 仪表板，通过 WebSocket 实时接收 L3 输出的 payload，以三栏布局渲染所有期权分析面板，**不做任何业务计算**，完全被动渲染后端 `ui_state`。

---

## 1. 核心设计原则

| 原则 | 实现方式 |
|------|----------|
| **解耦渲染** | 后端 Presenter 输出"徽章+标签"的结构，React 盲目渲染，无业务判断 |
| **单一数据源** | 全部数据来自 `useDashboardWS` hook 的 WebSocket payload |
| **零状态衍生** | 组件不自行计算任何衍生状态，直接读取 `payload.agent_g.data.ui_state.*` |
| **完整性降级** | 任何字段缺失时组件显示占位符 "—" 而非崩溃 |

---

## 2. 数据入口 (`useDashboardWS`)

```typescript
// src/hooks/useDashboardWS.ts
const { status, payload } = useDashboardWS()

// status: 'connecting' | 'connected' | 'disconnected'
// payload: 后端 SnapshotBuilder 输出的完整 JSON
```

连接到 `ws://localhost:8001/ws/dashboard`，内置自动重连。每收到一条消息立即更新 `payload` 状态，触发所有订阅组件重渲染。

连接成功时立即从 `/api/atm-decay/history` REST 拉取当日 ATM 历史序列（初始化图表）。

---

## 3. 三栏布局

```
┌─────────────────────────────────────────────────────┐
│                    HEADER (顶部)                     │
│  SPY价格 | ATM IV | IV制度 | WS连接状态 | 市场状态   │
├──────────────┬──────────────────┬────────────────────┤
│  LEFT 280px  │  CENTER (flex-1) │   RIGHT 320px      │
│  防御/分析   │    主图+叠加     │   战术/进攻        │
│              │                  │                    │
│ WallMigration│  AtmDecayChart   │  DecisionEngine    │
│              │  (Recharts折线图) │  TacticalTriad     │
│ DepthProfile │                  │  SkewDynamics      │
│  (GEX柱状图) │  AtmDecayOverlay │  ActiveOptions     │
│              │  (玻璃拟态卡片)  │  MtfFlow           │
│ MicroStats   │  GexStatusBar    │                    │
│  (4格指标栏) │  (底部悬浮条)   │                    │
└──────────────┴──────────────────┴────────────────────┘
```

---

## 4. 组件清单

### 顶部 Header（`center/Header`）
| Props | 来源 |
|-------|------|
| `spot` | `payload.spot` |
| `ivPct` | `agentBData.spy_atm_iv` |
| `ivRegime` | `fused.iv_regime` |
| `status` | WS 连接状态 |
| `marketStatus` | 本地时间判断 9:00~16:00 为 OPEN |
| `as_of` | `payload.timestamp` |

---

### 左栏 — 防御/分析

#### `WallMigration`
- **数据**: `uiState.wall_migration`（数组，来自 `WallMigrationPresenter`）
- **渲染**: Call Wall / Put Wall 历史位移表格，含方向箭头与颜色编码

#### `DepthProfile`
- **数据**: `uiState.depth_profile`（每 strike 的 GEX 值）+ `uiState.macro_volume_map`
- **渲染**: 水平双向柱状图（红=Put GEX，绿=Call GEX），标注现货价位与 Flip Level

#### `MicroStats`
- **数据**: `uiState.micro_stats`（`{net_gex, wall_dyn, vanna, momentum}` 各含 label/badge）
- **渲染**: 4格小指标卡片，完全盲渲染徽章

---

### 中栏 — 主图

#### `AtmDecayChart`
- **数据**: `atmHistory`（`AtmDecay[]`，来自 REST history + WS 追加）
- **渲染**: Recharts `LineChart`，追踪一天内 ATM IV 随时间的衰减曲线

#### `AtmDecayOverlay`
- **数据**: `atm`（最新 ATM 快照），`spot`，`atmHistory`
- **渲染**: 玻璃拟态浮层，显示当前 ATM IV、Theta、隐含每日移动距离

#### `GexStatusBar`
- **数据**: `netGex`, `callWall`, `flipLevel`, `putWall`
- **渲染**: 底部悬浮状态条，显示 Net GEX（$M）、Call Wall、Put Wall、Flip Level

---

### 右栏 — 战术/进攻

#### `DecisionEngine`
- **数据**: `fused`（`{direction, confidence, weights, regime, explanation, components}`）
- **渲染**: 信号方向 + 置信度环形图 + 各分量权重流量图

#### `TacticalTriad`
- **数据**: `uiState.tactical_triad`
- **渲染**: VRP 状态 / Charm 方向 / Spot-Vol 相关性三合一卡片

#### `SkewDynamics`
- **数据**: `uiState.skew_dynamics`
- **渲染**: 标准化偏度值 + DEFENSIVE/NEUTRAL/SPECULATIVE 状态标签

#### `ActiveOptions`
- **数据**: `uiState.active_options`（Top-5 活跃合约数组）
- **渲染**: 期权列表，含 Strike、类型、Delta、Gamma、成交量、GEX 贡献

#### `MtfFlow`
- **数据**: `uiState.mtf_flow`（`{consensus, alignment, strength, timeframes: {1m,5m,15m}}`）
- **渲染**: 多时间框架 IV 流向，1m/5m/15m 各档方向指示条

---

## 5. payload → 组件 数据路由图

```
payload
 ├─ .spot                               → Header, GexStatusBar, AtmDecayOverlay
 ├─ .timestamp                          → Header.as_of
 ├─ .agent_g
 │    ├─ .signal                        → DecisionEngine（信号文本）
 │    └─ .data
 │         ├─ .fused_signal             → DecisionEngine（权重图）
 │         ├─ .agent_b.data
 │         │    ├─ .net_gex             → GexStatusBar
 │         │    ├─ .spy_atm_iv          → Header
 │         │    ├─ .gamma_walls         → GexStatusBar
 │         │    └─ .gamma_flip_level    → GexStatusBar, DepthProfile
 │         └─ .ui_state
 │              ├─ .micro_stats         → MicroStats
 │              ├─ .tactical_triad      → TacticalTriad
 │              ├─ .skew_dynamics       → SkewDynamics
 │              ├─ .active_options      → ActiveOptions
 │              ├─ .mtf_flow            → MtfFlow
 │              ├─ .wall_migration      → WallMigration
 │              ├─ .depth_profile       → DepthProfile
 │              ├─ .macro_volume_map    → DepthProfile
 │              └─ .atm                 → AtmDecayOverlay (最新快照追加到 atmHistory)
 └─ (REST /api/atm-decay/history)       → AtmDecayChart (初始化历史)
```

---

## 6. 技术栈

| 技术 | 用途 |
|------|------|
| React 18 + TypeScript | UI 框架 |
| Tailwind CSS | 工具类样式（暗色主题） |
| Recharts | ATM Decay 折线图 |
| WebSocket (原生) | 实时数据接收 |
| Vite | 构建工具，开发服务器 |

---

## 7. 关键文件

| 文件 | 职责 |
|------|------|
| `src/hooks/useDashboardWS.ts` | WS 连接管理，payload 解析 |
| `src/components/App.tsx` | 根组件，数据提取 + 三栏布局编排 |
| `src/components/center/Header.tsx` | 顶部状态栏 |
| `src/components/center/AtmDecayChart.tsx` | ATM IV 衰减折线图 |
| `src/components/center/AtmDecayOverlay.tsx` | ATM 玻璃拟态浮层 |
| `src/components/center/GexStatusBar.tsx` | GEX 底部状态条 |
| `src/components/left/WallMigration.tsx` | Gamma Wall 位移表 |
| `src/components/left/DepthProfile.tsx` | GEX 深度分布图 |
| `src/components/left/MicroStats.tsx` | 微型指标栏 |
| `src/components/right/DecisionEngine.tsx` | 融合信号 + 置信度展示 |
| `src/components/right/TacticalTriad.tsx` | VRP/Charm/SVolCorr 三合一 |
| `src/components/right/SkewDynamics.tsx` | 偏度状态 |
| `src/components/right/ActiveOptions.tsx` | 活跃期权列表 |
| `src/components/right/MtfFlow.tsx` | 多时间框架流向 |
| `src/types/dashboard.ts` | TypeScript 类型定义 |

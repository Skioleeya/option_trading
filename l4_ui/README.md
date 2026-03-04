# l4_ui — L4 前端表现层

> **Strangler Fig 模式** — 从 `frontend/` 完整迁移，与原版并存，验证通过后替换。

## 架构总览

```
L3 FrozenPayload (WebSocket JSON)
        │
        ▼
┌───────────────────────────────────────────────┐
│  ProtocolAdapter (WS 传输层)                    │
│  ├─ DeltaDecoder (JSON-Patch 差分解码)           │
│  ├─ ConnectionMonitor (5 态连接状态机)            │
│  └─ L4Rum (Performance API 可观测性)             │
└──────────────────┬────────────────────────────┘
                   │ applyFullUpdate / applyMergedPayload
                   ▼
┌───────────────────────────────────────────────┐
│  DashboardStore (Zustand + subscribeWithSelector) │
│  ├─ 字段级精确订阅 (selectSpot / selectFused…)      │
│  ├─ Sticky-key 保护 (wall_migration, depth…)      │
│  └─ ATM History 环形缓冲 (max 500)                 │
└──────────────────┬────────────────────────────┘
        ┌──────────┼──────────────┐
        ▼          ▼              ▼
  12 个 React.memo    AlertEngine     CommandPalette
  组件 (自主订阅)     (6 条机构规则)    (Ctrl+K)
```

## 快速开始

```bash
# 安装依赖
cd l4_ui
npm install

# 开发模式 (连接 ws://localhost:8001)
npm run dev

# 运行测试
npm test

# 类型检查
npx tsc --noEmit

# 生产构建
npm run build
```

## 文件结构

```
l4_ui/
├── src/
│   ├── store/
│   │   ├── dashboardStore.ts          ← Zustand 状态树 (Phase 1)
│   │   └── __tests__/
│   │       └── dashboardStore.test.ts ← 15 tests
│   ├── adapters/
│   │   ├── protocolAdapter.ts         ← WS 传输层 (Phase 1)
│   │   ├── deltaDecoder.ts            ← JSON-Patch 差分解码 (Phase 1)
│   │   └── __tests__/
│   │       ├── protocolAdapter.test.ts ← 8 tests
│   │       └── deltaDecoder.test.ts    ← 9 tests
│   ├── alerts/
│   │   ├── alertEngine.ts             ← 6 条告警规则引擎 (Phase 4)
│   │   ├── alertStore.ts              ← Toast 队列 Zustand store (Phase 4)
│   │   └── __tests__/
│   │       └── alertEngine.test.ts    ← 15 tests
│   ├── commands/
│   │   └── commandRegistry.ts         ← Ctrl+K 命令注册表 (Phase 4)
│   ├── observability/
│   │   ├── connectionMonitor.ts       ← 5 态连接状态机 (Phase 5)
│   │   └── l4_rum.ts                  ← 前端 RUM 可观测性 (Phase 2)
│   ├── hooks/
│   │   └── useDashboardWS.ts          ← 向后兼容 shim
│   ├── components/
│   │   ├── App.tsx                    ← 布局骨架 (零 props 传递)
│   │   ├── CommandPalette.tsx         ← Ctrl+K 命令面板 (Phase 4)
│   │   ├── AlertToast.tsx             ← 告警浮层 (Phase 4)
│   │   ├── center/
│   │   │   ├── Header.tsx             ← SPY 价格 / IV / 连接状态
│   │   │   ├── GexStatusBar.tsx       ← GEX 状态条
│   │   │   ├── AtmDecayChart.tsx      ← ATM 衰减图表 (Lightweight Charts)
│   │   │   └── AtmDecayOverlay.tsx    ← ATM 衰减覆盖层
│   │   ├── left/
│   │   │   ├── DepthProfile.tsx       ← 深度分布
│   │   │   ├── MicroStats.tsx         ← 微结构统计
│   │   │   └── WallMigration.tsx      ← 墙位迁移
│   │   └── right/
│   │       ├── DecisionEngine.tsx     ← 融合信号决策
│   │       ├── TacticalTriad.tsx      ← 战术三角
│   │       ├── SkewDynamics.tsx       ← 偏度动态
│   │       ├── ActiveOptions.tsx      ← 活跃期权
│   │       └── MtfFlow.tsx            ← 多时间框架资金流
│   ├── types/
│   │   ├── dashboard.ts               ← WS payload 类型定义
│   │   └── l4_contracts.ts            ← L3 对齐严格类型 (Phase 2)
│   ├── smoke_test.ts                  ← 开发环境 Mock 注入器 (Phase 5)
│   └── main.tsx                       ← 应用入口
├── package.json
├── tsconfig.json
├── vite.config.ts
└── vitest.config.ts
```

## 关键组件说明

| 组件 | 职责 |
|------|------|
| `DashboardStore` | Zustand 不可变状态树；`subscribeWithSelector` 中间件实现字段级精确订阅；Sticky-key 保护防止瞬态空值覆盖历史数据 |
| `ProtocolAdapter` | 纯传输层；指数退避自动重连；路由 full / delta / keepalive 三种消息类型 |
| `DeltaDecoder` | RFC 6902 JSON-Patch 解码；支持 `fast-json-patch` 就地应用；错误隔离不影响主流 |
| `ConnectionMonitor` | 5 态状态机 (`DISCONNECTED` → `CONNECTING` → `AWAIT_STATE` → `RUNNING` → `STALLED`)；心跳超时 3s 检测静默掉线 |
| `AlertEngine` | 6 条机构级规则 (信号翻转 / IV 升级 / GEX 翻转 / 墙位突破 / Flip 穿越)；滞后冷却防止告警疲劳 |
| `CommandPalette` | `Ctrl+K` 触发；模糊搜索；动态上下文 (实时价格 / 墙位) |
| `L4Rum` | Performance API mark/measure 记录 WS→渲染延迟；rAF 帧率监控；V8 堆内存跟踪 |

## 12 个组件 Zustand 订阅映射

| 组件 | Store Selector | React.memo |
|------|---------------|------------|
| `MicroStats` | `ui_state.micro_stats` | ✅ |
| `WallMigration` | `ui_state.wall_migration` | ✅ |
| `DepthProfile` | `ui_state.depth_profile` + `macro_volume_map` + `selectSpot` | ✅ |
| `Header` | `selectSpot` + `selectIvPct` + `selectConnectionStatus` + `fused.iv_regime` | ✅ |
| `GexStatusBar` | `selectNetGex` + `selectGammaWalls` + `selectFlipLevel` | ✅ |
| `AtmDecayOverlay` | `selectAtm` | ✅ |
| `AtmDecayChart` | `selectAtmHistory` | ✅ |
| `DecisionEngine` | `selectFused` | ✅ |
| `TacticalTriad` | `ui_state.tactical_triad` | ✅ |
| `SkewDynamics` | `ui_state.skew_dynamics` | ✅ |
| `ActiveOptions` | `ui_state.active_options` | ✅ |
| `MtfFlow` | `ui_state.mtf_flow` | ✅ |

## 告警规则 (AlertEngine)

| 规则 | 冷却时间 | 严重级别 |
|------|---------|---------|
| 信号方向翻转 (BULLISH ↔ BEARISH) | 30s | ⚠️ warning |
| IV Regime 升级 (NORMAL → HIGH) | 60s | ⚠️/🔴 |
| Net GEX 符号翻转 (正 ↔ 负) | 60s | ⚠️ warning |
| Spot 突破 Call Wall | 120s | 🔴 critical |
| Spot 突破 Put Wall | 120s | 🔴 critical |
| Spot 穿越 Gamma Flip Level | 90s | ⚠️ warning |

## 开发调试 (Smoke Test)

开发环境下，浏览器控制台可用 `window.mockL4`：

```javascript
// 强制修改 Spot 价格
mockL4.setSpot(560)

// 手动触发告警
mockL4.triggerAlert('critical', 'SIGNAL', '测试告警', '确认弹窗样式')

// 模拟断网
mockL4.simulateDisconnect()

// 模拟恢复
mockL4.simulateConnect()

// 注入完整 payload
mockL4.injectPayload({ type: 'dashboard_update', timestamp: '...', spot: 560, agent_g: {...} })

// 查看 RUM 指标
mockL4.getRum()
```

## 运行测试

```bash
npm test
```

**结果: 4 files, 47 passed (vitest 1.6 + jsdom)**

```
✓ src/store/__tests__/dashboardStore.test.ts        (15 tests)
✓ src/adapters/__tests__/deltaDecoder.test.ts       (9 tests)
✓ src/adapters/__tests__/protocolAdapter.test.ts    (8 tests)
✓ src/alerts/__tests__/alertEngine.test.ts          (15 tests)
```

## Phase 路线图

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 协议与状态解耦 (ProtocolAdapter / DeltaDecoder / DashboardStore) | ✅ |
| Phase 2 | 类型合约 (l4_contracts.ts) + 可观测性 (l4_rum.ts) | ✅ |
| Phase 3 | 12 组件接入 Zustand selector + React.memo 零 re-render | ✅ |
| Phase 4 | 命令面板 (Ctrl+K) + 告警引擎 (6 规则 + 冷却) | ✅ |
| Phase 5 | 连接状态机 + Smoke Test 注入器 + 全量验证 | ✅ |

## 依赖

```
运行时:
  react ^18.3          UI 框架
  zustand ^5.0         状态管理
  fast-json-patch ^3.1 JSON-Patch 差分
  lightweight-charts ^5 ATM 衰减图表
  recharts ^2.12       备用图表
  framer-motion ^11    动画
  lucide-react ^0.395  图标
  clsx / tailwind-merge  样式工具

开发时:
  vitest ^1.6          单元测试
  @testing-library     DOM 测试工具
  typescript ^5.2      类型检查
  vite ^5.3            构建工具
  tailwindcss ^3.4     CSS 框架
```

## 布局不变性声明

> **三栏布局 (280px left / flex-1 center / 320px right) 100% 保持不变。**
> 所有 12 个 UI 组件的 DOM 结构、CSS 样式、视觉表现与重构前完全一致。
> 重构仅涉及数据流管道 (props drilling → Zustand selector) 和基础设施 (WS adapter / Alert / Monitor)。

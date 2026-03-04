# L4 — 前端展示层 (Frontend Presentation Layer)

## 2025–2026 主流金融架构重构指引

> **定位**: L4 是系统的人机界面——将 L3 组装的结构化数据以机构级交易终端品质呈现，支持交易员的实时决策、回顾分析和自定义工作流。
>
> **架构宗旨 (2025–2026)**: 从"被动渲染 JSON payload"模式，全面迁移至 **Binary Protocol 解码 + WebGL/Canvas 高性能渲染 + Composable Widget Architecture + Offline-First PWA + Keyboard-Driven Workflow**。

---

## 1. 架构目标与度量标准

| KPI | 当前基线 (v3) | 2025 H2 目标 | 2026 目标 |
|-----|--------------|-------------|----------|
| 首次有意义渲染 (FMP) | ~1.5s | **< 500 ms** | **< 200 ms** |
| WS 消息处理 → DOM 更新 | ~30–80 ms | **< 10 ms** | **< 5 ms** (direct Canvas) |
| 内存占用 (1小时运行) | ~150–300 MB | **< 100 MB** (ring buffer) | **< 60 MB** |
| 帧率 (60fps 稳定性) | 80–95% | **> 98%** | **99.5%** (WebGL) |
| 移动端支持 | 无 | **响应式 PWA** | 原生 Tauri/Electron 备选 |

---

## 2. 前端架构 (Target State)

```
              L3 Multi-Channel Output
                       │
          ┌────────────▼────────────────┐
          │     L4 Frontend Runtime      │
          │                              │
          │  ┌──────────────────────┐    │
          │  │  Protocol Adapter    │    │  ← Protobuf / JSON 自动协商
          │  │  (binary decode)     │    │
          │  └──────────┬───────────┘    │
          │             │                │
          │  ┌──────────▼───────────┐    │
          │  │  State Store         │    │  ← Zustand + Immer (immutable)
          │  │  (delta merge)       │    │     增量更新, 字段级订阅
          │  └──────────┬───────────┘    │
          │             │                │
          │  ┌──────────▼───────────┐    │
          │  │  Widget Compositor   │    │  ← 可组合面板系统
          │  │  ├─ Recharts Panel  │    │     用户可拖拽/缩放/布局
          │  │  ├─ Canvas Panel    │    │
          │  │  ├─ WebGL Panel     │    │
          │  │  └─ Table Panel     │    │
          │  └──────────┬───────────┘    │
          │             │                │
          │  ┌──────────▼───────────┐    │
          │  │  Command Palette     │    │  ← 键盘驱动操作
          │  │  (Ctrl+K workflow)   │    │
          │  └──────────────────────┘    │
          │                              │
          └──────────────────────────────┘
```

---

## 3. 数据层重构

### 3.1 Binary Protocol Adapter

替代当前 JSON WebSocket 解析:

```typescript
// ProtocolAdapter — 透明处理 Protobuf 或 JSON
class ProtocolAdapter {
  private decoder: ProtobufDecoder | JSONDecoder;

  constructor(ws: WebSocket) {
    // 服务端通过首帧协商协议
    ws.binaryType = 'arraybuffer';
    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        this.decoder = new ProtobufDecoder();
      } else {
        this.decoder = new JSONDecoder(); // 向后兼容
      }
      const payload = this.decoder.decode(event.data);
      stateStore.applyUpdate(payload);
    };
  }
}
```

### 3.2 State Store — Zustand + 增量合并

```typescript
// Zustand store with delta merge support
interface DashboardState {
  spot: number;
  signal: SignalData;
  uiState: UIStateData;
  atm: AtmDecayData;
  version: number;

  // 操作
  applyFullUpdate: (payload: DashboardPayload) => void;
  applyDelta: (delta: DeltaPayload) => void;
}

const useDashboardStore = create<DashboardState>()(
  subscribeWithSelector((set, get) => ({
    // ...初始值
    applyFullUpdate: (payload) => set(payload),
    applyDelta: (delta) => set((state) => ({
      ...state,
      ...delta.changes,
      version: delta.version,
    })),
  }))
);

// 组件只订阅自己需要的字段 — 精确重渲染
function MicroStats() {
  const microStats = useDashboardStore((s) => s.uiState.micro_stats);
  // 仅在 micro_stats 变化时重渲染
  return <MicroStatsView data={microStats} />;
}
```

**优势**:
- 从全局 payload 驱动 → 字段级精确订阅
- 消除不必要的重渲染 (当前每条 WS 消息触发全树重渲染)
- 增量合并与状态版本控制

---

## 4. 渲染引擎升级

### 4.1 高频数据的 Canvas/WebGL 渲染

```
数据频率与渲染引擎选择:

  1Hz 低频面板 (TacticalTriad, SkewDynamics)
    → React DOM (SVG/HTML) ✓ 保持
  
  1Hz 中频图表 (AtmDecayChart, DepthProfile)
    → React + HTML Canvas (Recharts 2.x 或 Lightweight Charts)
  
  Sub-second 高频热力图 (Toxicity Heatmap, OFI Stream)
    → WebGL (regl / Three.js 2D) ← 新增
  
  Tick-level 实时数据 (L2 Orderbook, Trade Tape)
    → GPU-accelerated Canvas ← 2026 远景
```

### 4.2 ATM Decay Chart 升级

```typescript
// 从 Recharts 迁移到 Lightweight Charts (by TradingView)
// 原因: 更专业的金融图表 + 更低的内存占用 + GPU 加速
import { createChart, LineSeries } from 'lightweight-charts';

function AtmDecayChart({ data }: { data: AtmDecayPoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const chart = createChart(containerRef.current!, {
      layout: { background: { color: '#0a0a0f' } },
      grid: { vertLines: { color: '#1a1a2e' }, horzLines: { color: '#1a1a2e' } },
      timeScale: { timeVisible: true, secondsVisible: false },
    });

    const series = chart.addSeries(LineSeries, {
      color: '#00d4ff',
      lineWidth: 2,
    });
    series.setData(data);

    return () => chart.remove();
  }, [data]);

  return <div ref={containerRef} className="h-full w-full" />;
}
```

### 4.3 Depth Profile — WebGL 加速

```
当前: React SVG 柱状图 (500 个 DOM 节点)
目标: WebGL InstancedMesh (1个 draw call)

性能对比:
  SVG (500 bars): ~8 ms/frame, 150 MB memory
  WebGL Instanced: ~0.5 ms/frame, 20 MB memory
```

---

## 5. 可组合面板系统 (Widget Architecture)

### 5.1 核心概念

从固定三栏布局升级为**可自定义面板系统**:

```typescript
interface WidgetDefinition {
  id: string;
  title: string;
  component: React.ComponentType<any>;
  dataSelector: (state: DashboardState) => any;
  defaultSize: { w: number; h: number };
  minSize: { w: number; h: number };
  category: 'defense' | 'analysis' | 'tactical' | 'chart';
}

// 注册所有可用面板
const WIDGET_REGISTRY: WidgetDefinition[] = [
  {
    id: 'depth_profile',
    title: 'GEX Depth Profile',
    component: DepthProfile,
    dataSelector: (s) => s.uiState.depth_profile,
    defaultSize: { w: 4, h: 6 },
    minSize: { w: 2, h: 3 },
    category: 'defense',
  },
  // ... 所有面板
];
```

### 5.2 布局管理

```
预设布局:
  "Scalper":       [ DepthProfile(大), AtmDecay(大), MicroStats(小) ]
  "Macro Analyst": [ WallMigration(大), MtfFlow(大), TacticalTriad(中) ]
  "Full Dashboard": [ 全部面板默认三栏 ]

自定义:
  - 拖拽调整面板位置和大小 (react-grid-layout)
  - 保存到 localStorage / 云端
  - 支持多 monitor 分屏 (DetachPanel → 新窗口)
```

---

## 6. 键盘驱动工作流 (Command Palette)

### 6.1 Cmd+K 命令面板

```
交易员键盘快捷操作:

  Ctrl+K → 打开命令面板
    "show depth"     → 聚焦 Depth Profile
    "zoom atm"       → ATM Decay 放大
    "switch layout"  → 切换预设布局
    "export signals" → 导出当日信号为 CSV
    "alert vpin > 0.6" → 设置自定义警报

  全局快捷键:
    Space       → 暂停/恢复实时更新
    G           → 切换 GEX 显示模式 (abs / normalized)
    D           → 切换暗/亮主题
    1/2/3       → 快速切换布局预设
    Esc         → 关闭所有浮层
```

---

## 7. 离线与恢复能力

### 7.1 Offline-First PWA

```
┌──────────────────────────────────────────┐
│            PWA Architecture              │
│                                          │
│  Service Worker:                         │
│    ├─ 缓存 static assets (Workbox)      │
│    ├─ 离线时显示最后快照 + stale 标记   │
│    └─ 重连后自动从 /history 回填        │
│                                          │
│  IndexedDB:                              │
│    ├─ 最近 500 条快照缓存              │
│    ├─ 用户自定义布局存储               │
│    └─ 自定义警报规则存储               │
│                                          │
│  Background Sync:                        │
│    └─ 中断期间的 beacon 通知补发        │
└──────────────────────────────────────────┘
```

### 7.2 连接状态与恢复

```typescript
type ConnectionState =
  | 'connected'           // 正常
  | 'reconnecting'        // 自动重连中 (指数退避)
  | 'degraded'            // 连接正常但延迟 > 3s
  | 'offline'             // 完全断连 → 显示 stale 数据
  | 'maintenance'         // 服务端计划维护

// 可视化: Header 中使用颜色编码的连接状态指示器
// 绿 → connected, 黄 → degraded, 红闪 → reconnecting, 灰 → offline
```

---

## 8. 自定义警报系统

```typescript
interface AlertRule {
  id: string;
  name: string;
  condition: (state: DashboardState) => boolean;
  action: 'sound' | 'notification' | 'highlight' | 'popup';
  cooldown_ms: number;  // 防重复触发
}

// 示例预设警报
const PRESET_ALERTS: AlertRule[] = [
  {
    id: 'vpin_high',
    name: 'VPIN > 0.7',
    condition: (s) => s.uiState.depth_profile?.toxicity > 0.7,
    action: 'sound',
    cooldown_ms: 60_000,
  },
  {
    id: 'gex_flip',
    name: 'GEX Flip Detected',
    condition: (s) => s.uiState.micro_stats?.net_gex?.badge === 'negative',
    action: 'popup',
    cooldown_ms: 300_000,
  },
];
```

---

## 9. 技术栈升级路线

| 当前 | 2025 目标 | 2026 目标 |
|------|---------|---------|
| React 18 | **React 19** (use + Suspense) | React 19+ |
| Tailwind CSS | 保持 | 保持 |
| Recharts | **Lightweight Charts** (金融图表) | + WebGL 自定义渲染器 |
| WebSocket (原生) | **protobuf-ts** + 二进制 WS | + gRPC-Web 备选 |
| Vite | Vite 6 | Vite + RSPack 混合 |
| 无状态管理 | **Zustand** + subscribeWithSelector | 保持 |
| 无测试 | **Vitest + Testing Library** | + Playwright E2E |
| 无离线 | **PWA (Workbox)** | + Tauri 桌面版 |

---

## 10. payload → 组件 数据路由图 2.0

```
ProtocolAdapter (binary/JSON)
  │
  ├─ DeltaEncoder.merge → Zustand Store
  │
  │  Store Fields                    → Subscribers (precise)
  │  ├─ .spot                       → Header, GexStatusBar, AtmDecayOverlay
  │  ├─ .signal                     → DecisionEngine
  │  ├─ .uiState.micro_stats        → MicroStats (field-level sub)
  │  ├─ .uiState.tactical_triad     → TacticalTriad
  │  ├─ .uiState.skew_dynamics      → SkewDynamics
  │  ├─ .uiState.active_options     → ActiveOptions
  │  ├─ .uiState.mtf_flow           → MtfFlow
  │  ├─ .uiState.wall_migration     → WallMigration
  │  ├─ .uiState.depth_profile      → DepthProfile (WebGL)
  │  ├─ .uiState.macro_volume_map   → DepthProfile
  │  ├─ .atm                        → AtmDecayOverlay + AtmDecayChart
  │  └─ .version                    → 内部一致性校验
  │
  └─ AlertEngine.evaluate(store) → 警报系统
```

---

## 11. 三栏布局 2.0 (默认预设)

```
┌────────────────────────────────────────────────────────────────┐
│  HEADER: SPY $XXX.XX │ IV 18.5% │ ●Connected │ 09:30-16:00    │
│  ┌──────── Command Palette (Ctrl+K) ────────┐                  │
├──┤─────────────┬──────────────────┬──────────┤─────────────────┤
│  │  LEFT 300px │  CENTER (flex-1) │  RIGHT   │ ALERTS          │
│  │  可折叠     │  可拆分为多图表  │  320px   │ 浮层侧栏        │
│  │             │                  │          │                  │
│  │ WallMigr.   │  AtmDecay(LWC)  │ Decision │ ⚡ VPIN > 0.7   │
│  │ DepthProf.  │  [可替换为      │ Tactical │ ⚡ GEX Flipped  │
│  │  (WebGL)    │   Orderbook/    │ Skew     │                  │
│  │ MicroStats  │   Trade Tape]   │ ActiveOpt│ [自定义警报列表] │
│  │             │  GexStatusBar   │ MtfFlow  │                  │
│  │ [可折叠面板]│  [底部固定]     │          │                  │
└──┴─────────────┴──────────────────┴──────────┴─────────────────┘
```

---

## 12. 可观测性 (前端 RUM)

| 指标 | 工具 | 说明 |
|------|------|------|
| `l4.ws_msg_to_render` | Performance API | 消息到达 → DOM 更新延迟 |
| `l4.frame_rate` | requestAnimationFrame | 实时 FPS 监控 |
| `l4.memory_usage` | `performance.memory` | 堆内存趋势 |
| `l4.ws_reconnect_count` | 自定义计数器 | 重连频率 |
| `l4.user_interaction` | 自定义事件 | 命令面板使用率、布局变更 |

---

## 13. 迁移路线图

```
Phase 1 (2025 Q3): Zustand state store + precise subscriptions
Phase 2 (2025 Q4): Lightweight Charts + Canvas DepthProfile
Phase 3 (2026 Q1): Protobuf binary WS + DeltaEncoder client
Phase 4 (2026 Q1): Widget compositor (react-grid-layout) + 预设布局
Phase 5 (2026 Q2): PWA + 离线支持 + Command Palette
Phase 6 (2026 H2): WebGL 渲染器 + Tauri 桌面版 + 自定义警报
```

---

## 14. 关键文件（当前 → 目标映射）

| 当前文件 | 重构目标 | 备注 |
|---------|---------|------|
| `src/hooks/useDashboardWS.ts` | → `src/adapters/protocol_adapter.ts` + `src/store/dashboard.ts` | 分离协议与状态 |
| `src/components/App.tsx` | → `src/compositor/WidgetCompositor.tsx` | 可组合面板 |
| `src/components/center/AtmDecayChart.tsx` | → Lightweight Charts 实现 | 金融级图表 |
| `src/components/left/DepthProfile.tsx` | → `src/renderers/depth_profile_webgl.tsx` | WebGL 加速 |
| `src/types/dashboard.ts` | → `src/types/generated/` (from Protobuf) | 自动生成类型 |
| — (新文件) | `src/store/dashboard.ts` | Zustand store |
| — (新文件) | `src/alerts/engine.ts` | 自定义警报引擎 |
| — (新文件) | `src/compositor/CommandPalette.tsx` | Cmd+K 命令面板 |
| — (新文件) | `src/sw.ts` | Service Worker (PWA) |

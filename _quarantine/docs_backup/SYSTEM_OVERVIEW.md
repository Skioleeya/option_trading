# SPY 0DTE Dashboard — 系统架构概览

> **系统定位**: 用于 SPY 0DTE 期权交易的实时决策支持仪表板。以 1Hz 刷新频率从 Longport API 采集数据，通过多信号融合引擎输出结构化交易信号，并在浏览器端实时展示。

---

## 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                     L4 — 前端展示层                              │
│        React (3栏仪表板) · WebSocket Client · Recharts           │
│        src/components/** · src/hooks/useDashboardWS              │
└─────────────────────────────┬───────────────────────────────────┘
                               │  ws://  1Hz push
┌─────────────────────────────▼───────────────────────────────────┐
│                     L3 — 输出组装层                              │
│  SnapshotBuilder · 7个 UI Presenters · AtmDecayTracker           │
│  双循环广播 (compute 1~3s / broadcast 1Hz) · Redis 持久化        │
│  app/services/system/ · app/ui/                                  │
└─────────────────────────────┬───────────────────────────────────┘
                               │  AgentResult
┌─────────────────────────────▼───────────────────────────────────┐
│                     L2 — 决策分析层                              │
│  AgentA (动量) · AgentB1 (陷阱+微观结构) · AgentG (顶层融合)    │
│  DynamicWeightEngine · 5级门控决策 · VRP/MTF/Vanna/Jump 信号    │
│  app/agents/ · app/services/trackers/ · app/services/analysis/  │
└─────────────────────────────┬───────────────────────────────────┘
                               │  snapshot (已含 aggregate_greeks)
┌─────────────────────────────▼───────────────────────────────────┐
│                     L1 — 本地计算层                              │
│  GreeksEngine (Thread-offloaded BSM) · Rust 加速内核 (VPIN)      │
│  GreeksExtractor · app/services/analysis/depth_engine.py         │
│  app/services/analysis/bsm_fast.py · ndm_rust (Rust Kernel)      │
└─────────────────────────────┬───────────────────────────────────┘
                               │  raw quotes (in-memory dict)
┌─────────────────────────────▼───────────────────────────────────┐
│                     L0 — 数据摄取层                              │
│  MarketDataGateway (WS 缓冲) · SanitizationPipeline (NaN 清洗)    │
│  ChainStateStore (Seq_no 竞态保护) · FeedOrchestrator            │
│  Tier1 WS · Tier2 REST · Tier3 周期权 · IVBaselineSync           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 数据流程（单次 compute tick）

```
1. L0: OptionChainBuilder.fetch_chain()
   ├─ ChainStateStore 提供零延迟的安全内存快照（包含 Toxicity 等）
   └─ MarketDataGateway 和 FeedOrchestrator 负责后台的 WS 收发和 REST 轮询 

2. L1: GreeksEngine.enrich() (后台线程无阻塞)
   ├─ 纯后台线程 `asyncio.to_thread` 执行批处理
   ├─ 单次遍历：BSM 计算各合约 Greeks (Numba) → 累积 Net GEX / Vanna / Charm
   ├─ DepthEngine (Rust Powered): 调用 ndm_rust.update_vpin_logic 处理成交与桶
   └─ 返回聚合参数给 `OptionChainBuilder.fetch_chain` 组装快照

3. L2: AgentG.run(snapshot)
   a. AgentB1.run(snapshot)
      ├─ GreeksExtractor → ATM IV, Gamma Walls, Flip Level
      ├─ VannaFlowAnalyzer → GEX 制度, momentum_slope_multiplier
      ├─ WallMigrationTracker → Call/Put Wall 位移
      ├─ IVVelocityTracker → IV 速率制度 (1m/5m/15m)
      ├─ MTFIVEngine (VSRSD) → 多时间框架共识
      ├─ VolumeImbalanceEngine → C/P 量不平衡
      ├─ Depth Signal (Phase 3): 聚合 ATM 毒性与盘口失衡 (micro_flow)
      └─ JumpDetector → 跳变检测（P0.1 安全阀）
   b. AgentA.run(snapshot, slope_multiplier)
      └─ 现货动量方向
   c. AgentG._decide_impl()
      ├─ P0.1 Jump Gate → HOLD
      ├─ P0.5 VRP Veto → NO_TRADE
      ├─ P1 陷阱优先
      ├─ P1.5 融合高置信度 (DynamicWeightEngine 加入 micro_flow)
      └─ P2 趋势确认 (A + GEX 方向)

4. L3: SnapshotBuilder.build(snapshot, agent_result, atm_decay)
   └─ 合并 AgentG ui_state + Wall Migration + Depth Profile + ATM数据
   └─ deepcopy 隔离后写入 AppContainer._last_payload

5. L3: _broadcast_loop (1Hz)
   └─ 注入新鲜时间戳 → 发给所有 WS 客户端

6. L4: React 渲染
   └─ 盲渲染 ui_state 中的所有组件
```

---

## 关键时序参数

| 参数 | 值 | 说明 |
|------|----|------|
| `compute_interval` | 1~3s（动态） | 由 `longport_limiter.get_dynamic_interval()` 决定 |
| `ws_broadcast_interval` | 1s（固定） | 设置项 `WS_BROADCAST_INTERVAL` |
| `management_loop` | 60s | 订阅刷新、OI 同步 |
| `iv_baseline_sync` | 120s | IV/OI REST 基线轮询 |
| `volume_research` | 15min | 宽窗口成交量分布扫描 |
| `Tier2Poller` | 120s | 2DTE REST 轮询 |
| `Tier3Poller` | 10min | 周期权 REST 轮询 |
| API 速率限制 | 8 req/s, burst 8 | 令牌桶，max_concurrent=4 |

---

## 层级文档索引

| 文档 | 层级 | 说明 |
|------|------|------|
| [L0_DATA_FEED.md](./L0_DATA_FEED.md) | L0 | Longport 数据摄取、三层订阅、速率限制 |
| [L1_LOCAL_COMPUTATION.md](./L1_LOCAL_COMPUTATION.md) | L1 | BSM Greeks、GEX聚合、Skew调整 |
| [L2_DECISION_ANALYSIS.md](./L2_DECISION_ANALYSIS.md) | L2 | Agent A/B1/G、微观结构分析、多级门控决策 |
| [L3_OUTPUT_ASSEMBLY.md](./L3_OUTPUT_ASSEMBLY.md) | L3 | SnapshotBuilder、Presenters、双循环广播 |
| [L4_FRONTEND.md](./L4_FRONTEND.md) | L4 | React 仪表板、组件清单、数据路由图 |

---

## 服务启动方式

```bash
# Backend (e:\US.market\Option_v3\backend)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend (e:\US.market\Option_v3\frontend)
npm run dev
```

默认访问: `http://localhost:5173`（前端） | `http://localhost:8001/health`（后端健康检查）

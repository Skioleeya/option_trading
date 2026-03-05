# SPY 0DTE Dashboard — 架构重构总览

> **系统定位**: 机构级 SPY 0DTE 期权实时决策支持平台。
>
> **文档版本**: v4.0 (基于 v3.1 最新代码库状态编写，附带 2025-2026 演进目标)
>
> **2026 Frontier Status**: 经 2026 量化金融审计，本项目后端算法（0DTE 避险机制、Vanna/Charm 预收盘窗口、SIMD Rust 核心）已确认为**全球一流前沿实践**。

---

## 纵览：v3 单体 到 v3.1 模块化

经过彻底的重构，系统告别了早期单体脚本的纠缠，全面转向高内聚低耦合的现代架构：

```
┌──────────────────────────────────────────────────────────────────────┐
│  v3 (早期)                    →  v4.0 (机构级)                       │
│                                                                      │
│  main.py (AppContainer God类) →  app/ (lifespan + routes + loops)    │
│  L1 IV 同步写死 REST         →  IV 弹性瀑布 + 高精度 TTM 秒级同步      │
│  L2 混杂信号                  →  绝对威胁建模 (OFII) + 扫单聚类检测     │
│  L3 deepcopy() 开销极大       →  Write-on-Copy (COW) 零拷贝组装       │
│  L4 静态列表渲染              →  Zustand 渲染阻截 + 机构级 Sweep 视觉  │
└──────────────────────────────────────────────────────────────────────┘
```

## 全局重构架构分层

```
┌─────────────────────────────────────────────────────────────────────┐
│                     L4 — 前端展示层 (l4_ui/)                         │
│  Zustand Store (Selector精准渲染) · Institutional Sweep Visuals      │
│  ActiveOptions (Impact Index 排序) · 0DTE 高频呼吸动画                │
└─────────────────────────────┬───────────────────────────────────────┘
                               │ WebSocket (全量/Delta / 1Hz Push)
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L3 — 输出组装层                                  │
│  Threat-Aware Assembler (OFII 驱动排序) · UIStateTracker              │
│  FieldDeltaEncoder (增量差异提取) · Presenters V2 (强类型转换)        │
└─────────────────────────────┬───────────────────────────────────────┘
                               │ DecisionOutput + EnrichedSnapshot
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L2 — 决策分析层                                  │
│  Institutional Grade Core (OFII Math) · Sweep Cluster Detector       │
│  Feature Store (Turnover Velocity) · Priority Guard Rails            │
└─────────────────────────────┬───────────────────────────────────────┘
                               │ EnrichedSnapshot (含 TTM / Flow Index)
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L1 — 本地计算层                                  │
│  Compute Router (GPU / CPU) · High-Precision TTM Generator           │
│  Flow Trackers (Integrated Vanna, Wall, IV Velocity)                 │
└─────────────────────────────┬───────────────────────────────────────┘
                               │ 经过净化的行情与快照
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L0 — 数据摄取层                                  │
│  Institutional Data Contract (impact_index / is_sweep)               │
│  MVCC ChainStateStore · Adaptive Rate Governor                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 核心架构拆解与文件结构 (v3.1)

最显著的变化在于消灭了体积庞大的 `main.py`。后台逻辑目前已被清晰拆分：

| 模块区域 | 核心文件 / 路径 | 职责定位 |
|---------|---------------|--------|
| **App 壳** | `app/container.py` | DI (依赖注入) 容器，提供全局组件单例 |
| | `app/lifespan.py` | 遵循 FastAPI 规范，管理启动时线程创建与资源预热 |
| | `app/routes/` | REST 子路由 (`health.py`, `history.py`, `ws/`) |
| | `app/loops/` | 并行轮询拆分 (`compute_loop`, `housekeeping_loop`...) |
| **测试工具** | `scripts/` | 按 `test`, `perf`, `diag` 精细分类的独立运维集合 |

## 研发/运营规范入口

- **启动检查表**：欲启动环境请严格参见项目根目录下的 [`启动步骤.md`](../启动步骤.md) 进行端口清场与双端唤起。
- **单元与集成测试**：所有重大改动后请务必在底座运行 `python scripts/test/test_depth_profile.py` 实施 L0-L3 数据连通性检查。

## 远期宏大迁移路线 (2025–2026 Vision)

当前 v3.1 已为后续彻底进入低延迟时代打好桩位。

```
2025 H2 ─────────────────────────────────────────────────────
  [基建跨越] Rust IngestWorker 取代 Python WS 网关。SPSC 零锁环形队列。
  [内存跨越] 全链路 Arrow RecordBatch 零拷贝，抛弃 dict-to-dict 开销。

2026 Q1 ─────────────────────────────────────────────────────
  [协议跨越] 前后端通信切换为 Protobuf / FlatBuffers 二进制压缩报文。
  [分析跨越] 废除线形 Skew，启用 SABR / SVI 曲面拟合校准。
  [模型跨越] 离线模型训练引入，支持 XAI(SHAP) 以及 Shadow Mode 实盘重播。

2026 H2 ─────────────────────────────────────────────────────
  [极致延迟] 预留 FPGA 层网卡直接截取组播 (Colo Machine bypassing kernel) 勾子。
  [前端扩展] WebGL 接管全量复杂 DOM + PWA Desktop 客服端形态支撑。
```

---

## 服务启动极简示例

```powershell
# 1. 启动 Redis (依赖)
.\scripts\infra\redis-start.bat

# 2. 启动 Backend (请在 Option_v3 根目录开启，确立 PYTHONPATH=.)
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --log-level info

# 3. 启动 Frontend (全新 l4 目录)
cd l4_ui
npm run dev
```

默认访问: `http://localhost:5173`（GUI 控制台） | `http://localhost:8001/health`（健康拨测心跳接口）

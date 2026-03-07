# SPY 0DTE Dashboard — 架构重构总览

> **系统定位**: 机构级 SPY 0DTE 期权实时决策支持平台。
>
> **文档版本**: v4.5 (基于 2026 最新 Rust/Arrow 核心状态编写)
>
> **2026 Frontier Status**: 经过 2026 第一季度实证审计，本项目的高性能 Rust 采集层、Arrow 零拷贝 IPC 以及 301607 级联限频保护机制已确认为**全球一流前沿实践**。

---

## 纵览：v3 到 v4.5 混合动力跃迁

经过深度集成，系统现已完成从 "Python 单体" 到 "Rust/Python 生产力集群" 的跃迁：

```
┌──────────────────────────────────────────────────────────────────────┐
│  v3 (早期)                    →  v4.5 (机构级混合动力)               │
│                                                                      │
│  main.py (AppContainer God类) →  app/ (Gold Context Pre-Flight 启动) │
│  Python WS (高延迟/GC抖动)    →  Dual-Stack Gateway (Python/Rust 互备)│
│  Dict Serialization (内存损耗) →  Zero-Copy Arrow IPC (共享内存)      │
│  L1 IV 限频 (301607 崩溃)     →  Dual-Bucket Governor (加权限流)     │
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
│  Threat-Aware Assembler (OFII 驱动排序) · FieldDeltaEncoder         │
│  Row-Level Memoization (1k+ 行级优化) · Presenters V2                │
└─────────────────────────────┬───────────────────────────────────────┘
                               │ DecisionOutput + EnrichedSnapshot
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L2 — 决策分析层                                  │
│  Institutional Grade Core (OFII Math) · Sweep Cluster Detector       │
│  Feature Store (Turnover Velocity) · Multi-Agent Fusion Engine       │
└─────────────────────────────┬───────────────────────────────────────┘
                               │ EnrichedSnapshot (含 Native OFII/Sweep)
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L1 — 本地计算层                                  │
│  Rust Bridge (Zero-Copy Mmap) · Compute Router (GPU/CPU Hetero)      │
│  Flow Trackers (Integrated Vanna, Wall, IV Velocity)                 │
└─────────────────────────────┬───────────────────────────────────────┘
                               │ 共享内存 (Apache Arrow IPC)
┌─────────────────────────────▼───────────────────────────────────────┐
│                     L0 — 数据摄取层 (Native Rust)                    │
│  Native SDK Ingest · Core Pinning · Impact/Sweep Pre-Compute         │
│  Weighted Rate Limiter (301607 Fix) · Dual-Token Governor            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 核心架构拆解与文件结构 (v4.5)

系统通过 Rust 强化了感知能力，通过 Python 维持了业务敏捷性：

| 模块区域 | 核心文件 / 路径 | 职责定位 |
|---------|---------------|--------|
| **L0 Native** | `l0_ingest/l0_rust/` | [ACTIVE] Rust 原生网关，处理极速 WebSocket 与 Native Greeks 计算 |
| **IPC Bridge**| `l1_compute/rust_bridge.py` | [ACTIVE] 基于 Arrow 的零拷贝共享内存接入层 (Mmap) |
| **L1 Reactor** | `l1_compute/reactor.py` | 现代 L1 编排器，通过 RecordBatch 接收 L0 数据并下发 EnrichedSnapshot |
| **App 容器** | `app/container.py` | DI (依赖注入) 容器，提供全链路组件单例与 Gold Context 管理 |
| **测试工具** | `scripts/` | 包含 `live_market_test.py` (实盘) 与 `test_rust_bridge.py` (性能) |

## 研发/运营规范入口

- **启动检查表**：欲启动环境请严格参见项目根目录下的 [`启动步骤.md`](../启动步骤.md)。
- **核心构建**：修改 Rust 逻辑后，需执行 `maturin develop` 重新编译原生库。
- **性能验证**：定期运行 `python scripts/test_rust_bridge.py --stress` 确保 IPC 链路稳固。
- **测试入口统一 (2026-03-06)**：`pytest` 统一走 `scripts/test/run_pytest.ps1`，缓存目录固定 `tmp/pytest_cache`，禁止管理员上下文混跑（防止 `pytest-cache-files-*` 权限残留污染仓库根目录）。

## 关键变更记录 (2026-03-06)

- **MicroStats 墙体状态机模块化**：L3 将 `WALL DYN` 复合态判定拆分为独立状态机模块，`BREACH` 走 urgent 直通，其余状态保留去抖。
- **跨层语义一致性修复**：修复了 `BREACHED/DECAYING/UNAVAILABLE -> STABLE` 的错误折叠，确保 L1 风险态在 L4 面板保持原始含义。
- **Vanna 阈值稳健性修复**：`vanna_grind_stable_threshold` 运行时执行负阈值守卫，阻断配置误设导致的状态漂移。
- **SPY ATM IV 实时链路修复（版本契约）**：修复 `compute_loop` 传入 L1 的 `l0_version` 常量化问题，改为透传 L0 快照版本；`ChainStateStore` 提供单调 `version` 并由 `fetch_chain` 下发，保障 L2 `FeatureStore` 在新快照上强制失效 TTL 缓存，避免 `atm_iv/iv_velocity` 旧值滞留。
- **ATM Decay 越界修复（拼接契约）**：将换锚拼接从“百分比加法”升级为“复利因子拼接”，并在 L1 强制 `-100%` 下界、16:00 后停更、跨日状态重置，阻断 `CALL <-100%` 的语义越界。
- **跨层时间戳契约加固（P0 Debt Fix）**：`data_timestamp/timestamp` 统一绑定 L0 `as_of_utc`，L3 保持广播时钟独立，drift 统一以 `L2 computed_at - L0 source timestamp` 计算。
- **ATM 冷存写放大修复（P0 Debt Fix）**：ATM 衰减冷存从全量 JSON 重写切换为 JSONL 增量追加；恢复优先 JSONL 并兼容历史 JSON 数组文件。
- **P1 运行时观测探针（2026-03-06）**：在 compute loop 增加 `snapshot_version vs spy_atm_iv` 漂移探针，采用 3-tick confirm，输出开始/持续/恢复日志，并将诊断快照接入 `/debug/persistence_status`。
- **P1 L4 交互与渲染修复（2026-03-06）**：`l4:nav_*` 命令链路在 DepthProfile 端实现监听与最近 strike 回退；ATM 图表写入改为增量优先（append 走 `update`，回灌/重排回退 `setData`）。
- **P2 会话工具链收口（2026-03-06）**：
  - `scripts/new_session.ps1` 新增 `-Timezone`（IANA/Windows）并统一影响 session 路径时间与 `meta.yaml` 时间字段。
  - `scripts/validate_session.ps1` 新增 `-Strict` 硬门禁，要求 `commands/files_changed/tests_passed` 非空，并在严格模式下对目标 session 执行债务门禁。
  - 新增 `.github/workflows/session-validation.yml`，在 `pull_request + workflow_dispatch` 执行严格会话校验。
  - 严格模式增加运行产物卫生规则：`logs/*` 与 `data/atm_decay/atm*.json` 命中时需 `RUNTIME-ARTIFACT-EXEMPT` 才允许通过。
- **P2 L4 连接稳定性修复（2026-03-06）**：`ProtocolAdapter` 对全量/增量/keepalive 帧统一刷新连接心跳，修复前端误判 `RDS STALLED` 的黄灯假阳性。

## 远期宏大迁移路线 (Updated 2026 Vision)

当前 v4.5 已提前攻克了大部分 2025/2026 预设目标。

```
2025 H2 [ACHIEVED] ─────────────────────────────────────────────
  [基建跨越] Rust IngestWorker 取代 Python WS 网关。SPSC 零锁环形队列。
  [内存跨越] 全链路 Arrow RecordBatch 零拷贝，传输开销为 0。
  [可靠跨越] 加权双令牌桶 governor 彻底解决 301607 限频。

2026 Q1 ─────────────────────────────────────────────────────
  [协议跨越] 前后端通信切换为 Protobuf 二进制报文。
  [分析跨越] 启用 SABR / SVI 曲面拟合校准。
  [模型跨越] 引入 Shadow Mode 实盘重播。

2026 H2 ─────────────────────────────────────────────────────
  [极致延迟] 预留 FPGA 层网卡直接截取组播勾子。
  [前端扩展] WebGL 接管全量复杂 DOM 渲染。
```

---

## 服务启动极简示例

```powershell
# 1. 编译并安装 Rust 网关 (首次)
cd l0_ingest/l0_rust; maturin develop; cd ../..

# 2. 启动基础依赖与后端
.\scripts\redis-start.bat
$env:PYTHONPATH='.'; python -m uvicorn main:app --port 8001

# 3. 启动 GUI 控制台
cd l4_ui; npm run dev
```

默认访问: `http://localhost:5173`

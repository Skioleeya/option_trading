# SPX 0DTE 2026 前沿架构升级方案 (v4.0 蓝图)

基于您提供的 2024-2026 年微观结构前沿审计报告，以及当前系统 v3.1 版本的 L0-L4 架构全貌，以下是系统平滑过渡至 2026 顶级买方机构标准的详细升级方案。

## User Review Required

> [!IMPORTANT]
> **资源重分配确认**
> 实施 Vanna-Adaptive Windowing (VAW) 和 2DTE 桥接将导致 L1 层的计算负载与 L3/L4 的 WebSocket 载荷增加。我们需要确认当前架构是否已充分启用 **Rust SIMD** 和 **GPUGreeksKernel** 以应对动态爆发的节点数量。
> 另外，**Stochastic Wall Tracking (随机墙追踪)** 将原本的单 INT 标量值变更为 PDF 数组分布，前端 `DepthProfile` 需变更渲染逻辑为热力图模式。

---

## Proposed Changes

以下升级严格遵循从 L0 (微观摄取) -> L1 (量子计算) -> L2 (融合决策) -> L3/L4 (通讯渲染) 的流水线原则。

### L0 数据摄取层 (Data Ingestion Layer)

针对审计风险点：**缺乏 2DTE 对冲桥** 与 **经销商对冲盲区**

#### [MODIFY] L0 Tier 分层订阅与窗口管理器
- 引入 **Forward Delta Bridge (2DTE)**：在现有的分层架构中，除了 0D/1D/W 的组合，在临近下午 14:00 (Charm 曝露加速期) 必须对 2DTE 合约提升至 Tier 1 (WebSocket) 订阅，填补隔夜跳空对冲的流动性盲区。
- 引入 **Vanna-Adaptive Windowing (VAW)**：重构静态的 `+25/-35pt` 代码逻辑。当 `SanitizePipeV2` 侦测到盘中 VIX > 25% (或本地计算的跳跃判定阈值) 且触发 `JumpDetector` 警告时，单侧订阅窗口深度自动扩展至 `-80pt` 乃至更深区间，捕捉深度 OTM 的 **Negative Gamma Hotspots**。

---

### L1 本地计算层 (Local Computation Layer)

针对审计风险点：**依赖盘后 OI 滞后** / **静态墙滞后风险** / **VSS 缺乏**

#### [MODIFY] L1 计算路由与 Trackers 子系统
- 重构 GEX 引擎与引入 **Intraday Flow GEX (IFG) / VW-GEX**：现有 L1 `l1_rust` 侧已有 VPINv2 与 BBOv2。在此基础上，通过 Rust SIMD 识别每笔交易的激进方 (Aggressor 측)，基于盘中新增 Volume 构建 **Volume-Weighted GEX**。淘汰对前日清算所静态 OI 的重度依赖。
- 引入 **θ-Weighted Flip Tracker**：在 `l1_compute/trackers/` 新增 `ThetaFlipTracker` 类，不再以纯 Gamma 正负为界，以公式 `GEX / exp(-Theta_decay_weight)` 计算 Theta 惩罚，描绘出更加准确的、随时间流逝导致的经销商真实的“动态弃守线”。
- 升级 **Stochastic Wall Tracker**：在原 `WallMigrationTracker` 中，将确定性单一行权价升级为一个概率密度函数 (PDF)。
- 前沿功能引入 **Vanna-Vol-Surface Stitching (VSS)**：结合既定的 2026 Q1 SABR 拟合更新，通过 `ComputeRouter` 监控 Vanna-Slope 的形变。

---

### L2 决策分析层 (Decision & Analysis Layer)

确保计算下压出的高阶因子可以被无缝汇入信号和回测引擎。

#### [MODIFY] Feature Store (特征库) 与 Signal Generators
- 特征注水：将 L1 推送上来的 `VW_GEX`, `Theta_Flip_Drift`, 和 `VSS_Displacement` 压入 `Feature Store` 的 TTL Cache 中。
- 新增 `VolCrushPredictor` 信号生成器：接收 VSS_Displacement 与 IVVelocity 的交叉乘数，从而预判未来 300-500ms 的波动率崩塌拐点。加入 `AttentionFusion` 中的权重模型。

---

### L3 输出组装层 (Output Assembly Layer)

确保新的高维数据能轻量打包分发。

#### [MODIFY] Presenters 与 Delta Encoder
- 结构重构：更新 `UIStateTracker` (内含微观收束提取)。
- 为 `DepthProfilePresenterV2` 增加 **PDF 热力渲染支持**，并将原本下发的单一 Wall 值升级为 `[{strike, probability}, ...]` 的数组结构。
- 强化 `FieldDeltaEncoder` 的压缩能力，特别是针对可能随着 VAW 而膨胀的 ActiveOptions 数列。

---

### L4 前端展示层 (Frontend Presentation Layer)

供机构交易员一目了然的新 UI。

#### [MODIFY] Zustand Store 与 UI Widgets
- 在左侧侧边栏或是独立组件中，新增一个代表 2DTE 对冲压力的 **"Forward Delta Bridge"** Widget。
- **DepthProfile.tsx 重构**：使用热力图色彩过渡代替原有的单一强壁阻力条，呈现**随机墙 (Stochastic Wall)** 的厚度。
- 修改 **AlertEngine**：增加侦测到 `VAW_EXPANSION_TRIGGERED` (窗口暴风扩展) 和 `VOL_CRUSH_IMMINENT` (VSS 崩塌警报) 等紧急高等级事件流。

---

## Verification Plan

本方案涵盖 L0 到 L4 全链重构，需要极其慎重的递进式测试模式。

### Automated Tests
1. **L0 摄取沙盒回放测试**：利用 2025 年的 VIX Spike 日志重播数据流，验证 VAW（窗口自适应拓宽）是否能在检测到 VIX 跳峰后，瞬间拉取 -80pt 数据。
2. **L1 Rust SIMD 算力测试**：对新加装的 IFG 引擎和 VW-GEX 进行百万 Tick 并发测试。必须验证在 `chain_size >= 150` 并包含 2DTE 时，GPU CuPy 核计算时延仍然 < 2ms。
3. **L3 Field Delta 负载检测**：验证新的 Stochastic Wall 数组以及增加 2DTE 链数据对 `FieldDeltaEncoder` 的额外序列化消耗。

### Manual Verification
1. 观察本地 `npm run dev` 前端仪表盘（`http://localhost:5173`），手动确认 VSS 与 VAW 触发时的前端性能监控仪（L4Rum）未见明显的 FPS 丢帧或爆堆。
2. 调用系统自带的 `Hack Matrix` (通过 Ctrl+D 唤出) 查看 `raw_telemetry` 中新导入的 `IFG` 信号及数值变化幅度。

# Gemini 系统升级研究提示词 (2024-2026)

基于对当前系统 **L0-L4 (数据源到决策引擎)** 的逻辑分析，我为您生成了这套专用于“系统升级”的提示词。这些提示词旨在让 Gemini 搜索能够直接改进您 `DecisionEngine`、[TacticalTriad](file:///e:/US.market/Option_v3/l4_ui/src/components/right/TacticalTriad.tsx#9-11) 和 `Fusion Signal` 的前沿研究。

---

## 1. 升级决策融合算法 (DecisionEngine 2.0) `[Phase 26 PROPOSED]`

> **当前逻辑**：基于静态映射和动态权重的加权平均（Paper 1 & 4）。
> **升级方向**：寻找基于 Transformer 或神经网络的实时多模态融合方案。

```markdown
# Role: 量化算法架构师
# Context: 升级现有的 Multi-Signal Fusion Engine (L2 Layer)
# Current System: 使用 Vanna, Wall, IV Velocity, MTF, VIB 的动态权重引擎。

任务：请检索 2024-2026 年间关于“高频多信号异步融合 (Asynchronous Multi-Signal Fusion)”的顶级论文，并针对以下系统升级提出方案：

1. **处理信号滞后**：寻找论文（如 2025 年 ICML 或 Journal of Finance），讨论如何处理 L1 层不同频率信号（如 10ms 的 VPIN 与 1s 的 GEX）的同步与对齐问题。
2. **权重自适应进化**：目前系统使用 GEX-linked 权重。是否存在 2025 年后的研究，利用强化学习 (RL) 进行“在线权重博弈”，以应对 Reg-NMS 规则下的流动性剧烈变动？
3. **架构建议**：根据检索结果，我应该如何重构 `l2_decision/signals/fusion/dynamic_weight_engine.py`，以集成最新的“注意力机制 (Attention Mechanism)”来识别当前最具主导权的 Alpha 来源？

# Priority Logic: 
- 关注可直接转化为 Python/PyTorch 代码的研究。
- 排除无法处理逐笔数据 (Tick Data) 的宏观模型。
```

---

## 2. 增强战术指标精度 (TacticalTriad 升级) `[L1 STABILITY RESTORED]`

> **当前逻辑**：跟踪 VRP (Veto), Charm (Dynamic), S-VOL (Regime)。
> **升级方向**：引入“隐式风险估值”与“二阶希腊值微观联动”。

```markdown
# Role: 衍生品定价专家
# Task: 提升 TacticalTriad (VRP, Charm, Svol) 的预测能力

背景：我们的系统目前跟踪 VRP (基于 Muravyev 论文) 和 Charm (Time-decay Delta-hedging)。

请搜索 2024-2026 年关于 0DTE 选项“二阶希腊值 (Vanna/Color/Regga)”的最新微观结构研究：
1. **Charm 溢价优化**：寻找关于“收盘前 2 小时 (Last 2 Hours) Charm 涌动的非线性加速”的最佳建模方案。
2. **S-VOL 替代指标**：是否存在比单纯的 IV Skew 更能反映“做市商对冲溢价”的替代指标（例如：IV Surface Curvature Adjoint 等 2025 年新方向）？
3. **实证建议**：这些前沿论文提到的“微观动力学”如何直接映射到我们的 `AgentG.decide()` 逻辑中，以减少虚假突破 (Fake Breakouts)？

# Search Constraints:
- 针对 SPX / SPY 0DTE 市场。
- 必须包含 2025 年后的实证数据支持。
```

---

## 3. 优化流量强度识别 (ActiveOptions 3.0) `[GPU MANDATE ENFORCED]`

> **当前逻辑**：D+E+G 复合得分排序。
> **升级方向**：利用卷积网络 (CNN) 或路径图 (Graph) 识别大单路径。

```markdown
# Role: 订单流建模专家 (Order Flow Expert)
# Task: 升级 ActiveOptions 的排序与流量识别算法 (DEG-FLOW)

任务：针对 2024-2026 年散户与机构在 0DTE 上的交易行为，请搜索：
1. **隐藏单探测**：如何改进现有的 FlowEngineG (基于历史 OI 变动)，引入最新的“逐笔流量预测 (Tick-by-tick Flow Labeling)”深度学习模型？
2. **聚类分析**：查找 2025 年关于“期权异动聚类 (Option Activity Clustering)”的研究。如果 10 个附近的 Strike 同时出现异常 Flow，该如何修正单个 Strike 的 Flow Z-Score？
3. **升级建议**：如何将 `l3_assembly/presenters/ui/active_options/presenter.py` 的算法，从简单的 Z-Score 排序升级为基于“订单流冲击指数 (Impact Index)”的排序？

# Sources: 
- arXiv:q-fin.TR (Trading and Market Microstructure)
- Risk.net 2025 技术特辑
```

---

## 4. 预测 IV 突发漂移 (SkewDynamics 升级) `[ARROW IPC VERIFIED]`

> **当前逻辑**：基于 `IVVelocityTracker` 的线性状态映射。
> **升级方向**：非参数化 IV 表面跳跃检测。

```markdown
# Role: 随机波动率研究员
# Task: 搜索 2024-2026 IV 跳跃 (Jump) 与 漂移 (Drift) 的非平稳态建模

背景：系统目前使用 `JumpDetector` 处理价格冲击。

请协助通过 Gemini 搜索：
1. **非平稳态预测**：寻找 2024 年末至 2025 年发表的，关于“波动率漂移 (V-Drift)”在高频场景下的最新预测算法。
2. **Skew 反转警报**：寻找关于“Skew 反转作为市场局部顶点 (Local Top/Bottom)”的最新统计验证论文。
3. **实现路径**：如何重写 `l1_compute/analysis/iv_velocity_tracker.py`，使其能够支持对“波动率表面二阶导”的实时捕捉？
```

---

## 💡 使用建议

1.  **输入分析**：在向 Gemini 提问前，先告诉它：“我已经分析了我的系统，它分为 L0-L4 层，L2 是基于加权信号的 [AgentG](file:///e:/US.market/Option_v3/l2_decision/agents/agent_g.py#18-537)”。这样 Gemini 会给出更有针对性的建议。
2.  **代码转换**：在 Gemini 找到论文后，明确要求：“请参考该论文第 [X] 节的数学描述，为我的 Python `dynamic_weight_engine.py` 写一个重构草案”。
3.  **对标 SOTA**：要求 Gemini 对比您的系统逻辑与论文逻辑，找出“性能欠缺的具体指标”。

# Gemini 量化金融研究 (2024-2026) 提示词指南

作为量化架构师，我为您整理了一套针对 2024-2026 年顶级论文的检索与分析模版。这套模版通过 **角色设定 (Persona)**、**任务拆解 (Chain of Thought)** 和 **精细化过滤** 来最大化 Gemini 的推理能力。

---

## 1. 宏观趋势检索模版 (Macro-Trend Discovery)

> **目标**：识别 2024-2026 年间市场的核心技术转向。

```markdown
# Role: 资深金融量化研究员 (Senior Quant Researcher)
# Task: 检索并概括 2024-2026 年顶级量化金融趋势

请作为一名专注于 SOTA (State-of-the-Art) 技术的量化研究员，利用你最新的知识库（包括对 2024-2026 年市场事件的理解），执行以下任务：

1. **确定关键词**：列出 5 个在 2024-2026 年间被顶级投行和对冲基金频繁提及的量化术语（如：Generative Alpha, High-frequency GEX, RL-based Execution 等）。
2. **论文检索指南**：在 arXiv (q-fin), SSRN, 和 Journal of Financial Economics 的最新发布的预印本及录用文章中，搜索与这些关键词相关的顶级论文题目及摘要。
3. **技术路线图**：重点分析从传统的统计模型向 LLM-Driven 决策模型转化的具体路径，并指出当前的“工业标准”是什么。
4. **输出要求**：请以 Markdown 表格形式列出 3-5 篇最重要的论文，包含：题目、作者、发表/录用时间、核心创新点、引用价值分 (1-10)。

# Constraints:
- 必须专注于 2024-2026 年的时间窗口。
- 排除低质量的、通俗化的金融读物，仅讨论学术或具备严谨实证研究的行业报告。
```

---

## 2. 针对特定领域深度挖掘 (Deep-Dive: Options & Microstructure)

> **目标**：解决具体的业务痛点（如 0DTE, IV 预测, 订单流失衡）。

```markdown
# Role: 量化交易架构师 (Quant Trading Architect)
# Task: 深度拆解 0DTE 与 GEX 领域的顶级研究 (2024-2026)

我正在优化我们的 SPX 0DTE 交易系统。请针对 2024 年至今在选项定价与微观结构领域的突破性进展，协助我：

1. **核心逻辑定位**：检索并详细说明目前如何利用“动态波动率锚点”或“隐式订单流分析”来预测 Gamma Squeeze。
2. **数学模型对比**：对比 2 篇以上 2025 年发布的顶级论文，分析它们在处理非对等流动性 (Asymmetric Liquidity) 时的数学建模差异。
3. **实操性评估**：对于提到的论文，请概括其模型是否易于在分布式 Python 框架下进行在线重校准 (Online Recalibration)。
4. **代码原型建议**：基于最近的论文思路，给出一个核心估值函数或特征提取器的伪代码逻辑。

# Format:
- 请使用严谨的数学术语（布朗运动、随机波动率、马尔可夫决策过程等）。
- 输出中文解释，但保留核心英语学术名词。
```

---

## 3. 跨学科交叉检索 (Interdisciplinary: AI + Finance)

> **目标**：寻找利用大模型进行特征工程或交易执行的最新方法。

```markdown
# Role: AI x Quant 算法专家
# Context: 2024-2026 Generative AI in Finance Revolution

请利用交叉学科视野，寻找 2024-2026 年间利用 Transformer、Diffusion Model 或 Reinforcement Learning 赋能金融交易的顶级应用方案：

1. **跨模态数据处理**：是否存在将 L1 逐笔数据转化为“图像语义”或“时序向量”进行预测的顶级论文？
2. **多智能体博弈 (Multi-Agent)**：寻找 2025 年关于 LLM 智能体在限价单簿 (LOB) 中进行纳什均衡博弈的研究。
3. **可解释性 AI (XAI)**：针对顶级对冲基金强调的“模型可解释性”，找出最新的针对量化特征重要性归因的研究。

# Search Sources Priority:
- ICML / NeurIPS (Finance Track)
- Journal of Mathematical Finance
- Quantitative Finance (Journal)
```

---

## 4. 论文评价与总结模版 (Paper Reviewer Mode)

> **技巧**：当你有了具体的论文列表或 PDF 全文后，使用此提示词让 Gemini 提取“干货”。

```markdown
# Role: 顶级学术期刊审稿人
# Task: 对以下量化论文进行“实战价值”审计

论文名称/内容：[在此处粘贴内容或提供详细摘要]

请从以下维度进行硬核分析：
1. **创新点是否虚构**：该论文的方法论在 2024-2026 年的高速交易环境下是否具有鲁棒性？是否存在“回测幸存者偏差”？
2. **算力经济性**：实现该算法通常需要的计算资源等级（单机服务器 vs 集群架构）。
3. **Alpha 衰减风险**：评估该方法如果被市场周知，其超额收益的饱和度及衰减周期预测。
4. **技术栈映射**：将论文中的数学逻辑，对应到 Python (numpy/pytorch/polars) 的具体实现建议。
```

---

## 💡 使用小贴士 (Pro Tips by Quant Architect)

1. **多级对话 (Iterative Search)**：先用“趋势检索”确定 3 个关键词，再用“深度挖掘”根据关键词找论文，最后用“审计模版”对单篇论文进行代码化解析。
2. **引用验证 (Citation Cross-Check)**：Gemini 有时会产生幻觉，务必在拿到题目后，询问：“请给出这篇论文的 arXiv 编号或 DOI 链接”，以确保其真实存在。
3. **连接实时 (Live Web Search)**：确保开启 Google Search 插件功能，因为 2025-2026 年的预印本论文更新速度极快。

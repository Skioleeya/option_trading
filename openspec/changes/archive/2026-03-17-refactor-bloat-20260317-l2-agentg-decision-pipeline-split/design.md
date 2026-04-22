## Design Summary

AgentG 采用 orchestration + support helpers 的双层结构：

- `agent_g.py` 保留流程编排、状态机持有与外部接口。
- `agent_g_decision_support.py` 承担纯逻辑计算：
  - snapshot 读值归一化
  - ATM 微结构聚合
  - micro flow 信号构建
  - dealer squeeze 标记抽取
  - fused_signal payload 构造

## Compatibility

- `AgentG.decide()` 输入输出签名不变。
- 保留 VRP/MTF/GEX/Jump gate 既有决策顺序。

## Quant Targets (Stage-1)

- `_decide_impl` 长度显著下降（目标 <= 45% baseline）。
- `_decide_impl` CC 显著下降（目标 <= 50% baseline）。
- 行为回归：关键分支结果等价。

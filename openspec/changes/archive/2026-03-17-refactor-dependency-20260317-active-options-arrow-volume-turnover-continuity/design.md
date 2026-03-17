## Design Summary

子提案采用“合同先行、行为不扩散”的最小侵入策略：

1. 明确 `volume/current_volume/turnover` 字段在 L0 快照与 L1 Arrow 的一一映射。
2. 确保 housekeeping 读取链路可拿到 `current_volume` 与 `turnover`，避免仅依赖 `volume`。
3. 保持 ActiveOptions 过滤语义可审计，避免引入隐式魔法逻辑。

## Constraints

- 不改变层级方向：`L0 -> L1 -> L2 -> L3 -> L4`。
- 不引入跨层耦合与私有成员跨层访问。
- 不引入复杂函数与深层嵌套分支。
- 不引入垃圾代码（调试残留、重复逻辑、临时分支）。

## Validation Plan

1. 合同测试：字段在 Arrow 输出与下游读取均可观测。
2. 行为测试：`min_volume` 过滤输入在低活跃场景下具备可解释性。
3. 回归测试：`scripts/test/run_pytest.ps1` 目标用例通过。
4. 严格门禁：`scripts/validate_session.ps1 -Strict` 通过并留痕。

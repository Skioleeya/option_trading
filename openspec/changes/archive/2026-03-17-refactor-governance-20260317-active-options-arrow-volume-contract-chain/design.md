## Design Summary

采用“父治理 + 子执行”最小风险路线：

1. 父提案只定义边界、阶段、量化门槛，不直接改 runtime。
2. 子提案按依赖顺序推进：dependency -> nesting -> bloat -> magic-number。
3. 修复路径覆盖 `L0 快照字段 -> L1 Arrow schema -> housekeeping 归一化 -> ActiveOptions 过滤输入`。
4. 保持 `L0 -> L1 -> L2 -> L3 -> L4` 方向不变，禁止任何逆向导入。

## Governance Constraints

- 禁止模块耦合：不允许跨层反向依赖。
- 禁止复杂嵌套：关键函数嵌套深度受控，优先早返回。
- 禁止复杂函数：核心函数必须可拆、可测、可审计。
- 禁止垃圾代码：不得引入重复逻辑、调试遗留、无意义兼容分支。

## Metrics

- 合同连续性：`current_volume/turnover` 在目标链路可观测且语义一致。
- 占位噪声：`No options above min_volume threshold` 触发频率应可解释并可量化对比。
- 质量门禁：复杂度/嵌套/函数长度/重复率满足阈值。
- 严格门禁：`scripts/validate_session.ps1 -Strict` 通过。

## Validation Plan

1. 子提案完成后执行相关 pytest（通过 `scripts/test/run_pytest.ps1` 入口）。
2. 执行边界扫描与质量门禁，确认无耦合扩散。
3. 执行 strict 校验并留痕。

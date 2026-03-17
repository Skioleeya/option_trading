## Design Summary

治理采用“先边界、后拆分、再收口”路线：

1. `dependency` 子提案先抽离 `OptionChainBuilder` 的桥接/转换/分发职责，明确中立模块接口。
2. 第二子提案对 `option_chain_builder.py` 做文件级拆分，确保单文件 <= 450 行、单职责。
3. 第三子提案对 `extractors.py` 做主题化拆分（flow/vol/skew/rv），确保单文件 <= 450 行、单职责。
4. 父提案负责汇总 before/after 指标与风险闭环。

## Governance Constraints

- 单文件硬门槛：`<= 450 LOC`（runtime 与核心治理文件）
- 单文件单一职责：一个主编排职责 + 明确 helper 边界
- 层级方向不变：`L0 -> L1 -> L2 -> L3 -> L4`
- 无跨层私有成员访问，无 wildcard import

## Metrics

- 单文件行数：超标文件清零（目标文件全部 <= 450）
- 圈复杂度：关键函数 <= 10
- 嵌套深度：关键函数 <= 3
- 反模式命中：0
- strict validation：PASS

## Validation Plan

每个子提案完成后执行：

1. `scripts/test/run_pytest.ps1` 相关回归
2. 架构边界扫描与反模式扫描
3. `./scripts/validate_session.ps1 -Strict`

父提案收口执行：

- 汇总三子提案指标对比
- 全量 strict 门禁留痕

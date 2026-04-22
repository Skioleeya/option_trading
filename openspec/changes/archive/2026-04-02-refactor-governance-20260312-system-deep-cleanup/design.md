## Design Summary

父提案采用“治理先行，分阶段收敛”机制：

1. `dependency` 先处理边界解耦，确保后续重构不跨层污染。
2. `nesting` 在边界稳定后压平控制流，降低热路径分支复杂度。
3. `bloat` 在结构清晰后拆分超长函数/类，提取中立服务模块。
4. `magic-number` 最后统一常量治理，避免在前序阶段反复改名。

## Metrics Governance

- 最大嵌套深度 <= 3（热路径 <= 2）
- 圈复杂度 <= 10（热路径 <= 8）
- 函数长度 <= 80 LOC
- 类长度 <= 400 LOC
- 重复逻辑下降 >= 40%
- 业务魔法数治理率 >= 80%（except 0/1/-1）
- 架构违规 import = 0
- 循环依赖 = 0
- 回归失败 = 0

## Risk Grading

- P0: 层级违规、合同破坏、回归失败
- P1: 指标不达标、热路径性能回退
- P2: 文档/SOP 同步缺失

## Validation Plan

每个子提案完成后必须执行：

1. 边界扫描（policy 规则）
2. 主题相关 pytest（通过 `scripts/test/run_pytest.ps1`）
3. 指标对比记录（before/after）

父提案收口必须执行：

- `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Design Summary

本治理链路按“先连续性、后性能”执行：

1. 子提案-1 修复 L1 空快照 metadata 透传断点，确保降级路径语义连续。
2. 子提案-2 修复 L0 fallback 快照诊断字段缺口，确保 L0->L4 诊断链不断。
3. 子提案-3 推进 L0->L1 Arrow 直通，减少每 tick dict->Arrow 转换开销。
4. 父提案统一汇总量化指标、测试结果、strict 门禁证据。

## Governance Constraints (Hard)

- 禁止使用复杂函数：函数职责单一，保持短小可测试。
- 禁止使用魔法数字：所有阈值/状态码必须常量化。
- 禁止使用复杂嵌套：优先 guard clause 与分支下沉。
- 禁止模块耦合：仅允许 `L0 -> L1 -> L2` 单向依赖。

## Contract Constraints

- `source_data_timestamp_utc` 必须在降级路径持续透传。
- `rust_active/shm_stats` 必须在异常/未初始化路径稳定输出。
- `version` 语义必须绑定 L0 快照版本，不得复用计算时间。

## Validation Plan

每个子提案完成后必须执行：

1. `scripts/test/run_pytest.ps1` 目标回归。
2. 架构边界扫描（必要时 `-FullRepoArchitectureScan`）。
3. `scripts/validate_session.ps1 -Strict`。

父提案收口必须执行：

- 汇总 before/after 指标与风险清单。
- 提供 strict 输出摘要与剩余债务记录。

## Design Summary

采用显式合同补齐策略：

1. 提取 fallback 共享状态构造器，统一输出 `rust_active/rust_shm_path/shm_stats`。
2. `uninitialized` 与 `error` 两类快照复用统一默认诊断结构。
3. 保证主路径 `compose_fetch_chain_payload()` 与现有状态构造保持兼容。

## Constraints

- 降级快照必须可被 compute loop/L1/L3 无异常消费。
- 状态字段语义清晰：`UNINITIALIZED`、`ERROR` 与 `DISCONNECTED` 区分。
- 不修改正常主路径的诊断逻辑。

## Hard Governance Prohibitions

- 禁止使用复杂函数：fallback 构造逻辑拆成小函数。
- 禁止使用魔法数字：head/tail 默认值常量化。
- 禁止使用复杂嵌套：扁平返回结构。
- 禁止模块耦合：仅在 L0 文件内闭环。

## Validation Plan

- `scripts/test/run_pytest.ps1 l0_ingest/tests/test_fetch_chain_components.py`
- 校验 fallback 快照关键字段稳定存在
- `scripts/validate_session.ps1 -Strict`

## Design Summary

采用最小侵入修复策略：

1. `_empty_snapshot()` 增加 `extra_metadata` 参数并保持默认兼容。
2. 所有降级早返回路径统一传入调用侧 metadata。
3. 仅做透传，不改写 metadata 内容，避免语义漂移。

## Constraints

- 保持 `EnrichedSnapshot.version` 语义不变。
- 保持 `extra_metadata` 结构不变。
- 不引入新的跨模块依赖。

## Hard Governance Prohibitions

- 禁止使用复杂函数：只做参数透传与赋值。
- 禁止使用魔法数字：不新增阈值常量。
- 禁止使用复杂嵌套：仅 guard clause。
- 禁止模块耦合：不引入新层级 import。

## Validation Plan

- `scripts/test/run_pytest.ps1 l1_compute/tests/test_reactor.py`
- 覆盖降级路径 metadata 透传断言
- `scripts/validate_session.ps1 -Strict`

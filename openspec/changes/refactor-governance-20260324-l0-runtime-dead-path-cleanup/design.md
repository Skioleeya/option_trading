## Context

`l0_ingest/v2` 已成为 L0 唯一正式工作树。本次治理不改变运行时业务语义，只清理静态结构噪声：

1. `source/runtime` 中存在未接入 `factory.py` / `facade.py` 的孤立 adapter。
2. `normalize/events` 中并存现役 `StateEventProcessor` 与历史 `ChainEventProcessor`。
3. `l0_ingest/tests/v2/test_quote_runtime.py` 超过 400 行，违反仓库文件长度上限。

## Design

### Runtime Side Path Cleanup

- 删除未被主链路使用的 `longport_adapter.py`。
- 保留 `RustQuoteRuntime` / `PythonQuoteRuntime` 作为 `source/runtime` 现役 provider。
- 调整 `base_feed.py` 说明，避免继续把已删除 adapter 作为正式实现文档化。

### Event Processor Convergence

- 删除 runtime-dead 的 `ChainEventProcessor`。
- 用 `StateEventProcessor` 单测覆盖现役事件处理路径，避免删除遗留件后测试盲区扩大。

### Test File Bloat Cleanup

- 将 `test_quote_runtime.py` 拆分为共享 support 模块和聚焦测试文件。
- 保持行为不变，仅消除长度违规并改善后续维护边界。

## Risk and Rollback

- 风险低：删除对象均未接入现役 runtime 工厂或导出链路。
- 若回归失败，可按文件级回滚 dead-path 删除和测试重组，不影响 L0 合同。

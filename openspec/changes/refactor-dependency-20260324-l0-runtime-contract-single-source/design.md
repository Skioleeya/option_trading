## Design Summary

1. Rust runtime 订阅路径改为显式 reconcile：首次 `start`，后续 symbol 集变化时执行 `stop -> start(updated set)`，禁止只更新 Python 跟踪集合。
2. 规范化 helper 下沉到 `normalize/pipeline/sanitization.py`，sync support 与 poller 只调用统一导出，不再各写一套 IV/OI parser。
3. `services/subscription/metadata.py` 统一承接 expiry scan / strike metadata / tier row builder，供 `SubscriptionManager`、Tier2、Tier3 共享。
4. `ChainStateStore` 维护最近一次 L0 source update；snapshot projection 直接消费该时间并移除 legacy compute fallback 字段。

## Boundary Contract

- 允许：L0 内部 `source -> normalize -> state -> services -> projection -> facade` 继续单向流动
- 保持：`OptionChainBuilder` 外部 API、tier caches、governor telemetry、diagnostics 键连续
- 禁止：runtime 会话与 Python tracked set 脱节；poller / sync 自行复制 IV/OI 解析；snapshot projection 输出 legacy `aggregate_greeks/ttm_seconds`

## Validation Plan

- Runtime: Rust subscribe 首次启动、更新订阅集、failover 恢复三种路径均由测试覆盖
- Contract: `fetch_snapshot` 组件测试确认 `as_of/as_of_utc` 绑定 source time 且不含 legacy fields
- Regression: `scripts/test/run_pytest.ps1 l0_ingest/tests/v2` 与 `scripts/validate_session.ps1 -Strict`

## Design

### 1) Runtime failover self-heal

- 触发条件：`RustQuoteRuntime` REST 操作出现 connectivity 错误（`socket/token`, connect reset/refused/timeout 等）。
- 执行顺序：
  1. 记录失败端点
  2. 切换到下一 endpoint profile
  3. 若会话已启动：重建 gateway 并用 `tracked_symbols` 重订阅
  4. 对当前 REST 操作重试一次
- 上限：一次操作内最多一轮切换与一次重试，不做循环切换。

### 2) Diagnostics contract

- `RustQuoteRuntime.diagnostics()` 新增：
  - `failover_count`
  - `last_failover_error`
  - `last_failover_at_utc`
- `ActiveOptionsRuntimeService.get_diagnostics()` 新增：
  - `rows_total/rows_placeholder/rows_real/all_placeholder`
  - `empty_filter_count`
  - `last_empty_filter_at_utc`
  - `last_update_at_utc`
  - `min_volume_threshold`

### 3) Operational hotfix

- 启动脚本增加 `-HotfixActiveOptions`（自动 degraded）和 `-HotfixMinVolume`（默认 10）。
- 新增一次性验活脚本：先查 `/health`，再查 `/history` 的 `active_options` 非占位行（仅在 `chain_size > 0` 时强制）。

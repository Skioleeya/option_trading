## Design

### 1. Startup Bootstrap Must Consume Pending Restore First

- `bootstrap_intraday_anchor()` 在 startup retry 窗口内若发现 `_pending_restore_anchor` 非空，不再直接早退。
- 它会先调用既有 deferred restore helper，对 pending anchor 执行严格 restore/discard 判定。
- 若 pending anchor 成功恢复，则复用该 anchor 继续 decay 计算。

### 2. Discard Must Fall Through To Fresh Capture

- 若 pending anchor 因 distance check 等原因被丢弃，bootstrap 不得返回空转。
- 同一次 startup bootstrap 调用必须立刻继续 `_capture_anchor()`，从当前 snapshot fresh capture 同日新 ATM。

### 3. Verification

- 新增 L1 回归场景：pending restore anchor 因 distance discard 失败后，startup bootstrap 必须 fresh-capture 新 strike。
- 保持 opening tick suppress 语义不变；首个 `0/0/0` 仍不得写入主 history。

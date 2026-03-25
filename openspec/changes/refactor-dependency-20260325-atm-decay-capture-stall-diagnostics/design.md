## Design

### 1. Periodic Capture-Stall Forensics

- `AtmDecayTracker` 新增 `_capture_failure_streak`，仅在 fresh-capture 实际尝试后仍未拿到 anchor 时递增。
- streak 达到固定阈值倍数时输出 INFO 级日志，包含：
  - `failures`
  - `context` (`update` / `startup_bootstrap`)
  - `spot`
  - `chain`
  - `zero_dte`
  - `integer_strikes`

### 2. Pure Helper Boundary

- `anchor.py` 新增 `summarize_opening_chain_inputs()` 纯函数，只负责从 `chain + now` 计算 same-day 0DTE/整数 strike 汇总。
- `tracker.py` 负责 orchestration 和节流日志；`runtime.py` 只负责 reset/persist 时的 streak 生命周期管理。

### 3. Reset Semantics

- 以下路径必须把 `_capture_failure_streak` 清零：
  - `persist_anchor()` 成功锁锚
  - `invalidate_tracker()`
  - `reset_for_new_day()`

### 4. Verification

- 新增回归场景：当 `update()` 的 capture failure streak 达到阈值时，必须输出 stall INFO log。
- 同一测试继续验证后续成功 capture 会把 streak 重置为 `0`。

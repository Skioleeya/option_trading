# Fix: ATM Decay Anchor Capture Silent Stall Diagnostics

After the 657 anchor was invalidated (5 consecutive raw-pct failures with both legs not found in chain), the tracker enters a silent indefinite retry loop where [select_opening_anchor](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/anchor.py#54-143) returns [None](file:///e:/US.market/Option_v3/l1_compute/tests/test_atm_decay_modular.py#288-297) on every tick because the L0 chain only contains 1 0DTE contract. All failure paths in [select_opening_anchor](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/anchor.py#54-143) log at `DEBUG` level, making the stall invisible.

## User Review Required

> [!IMPORTANT]
> The backend (PID 12996) is still running with `anchor=None`. Market is open. A restart would likely fix the immediate issue by re-acquiring a full chain, but won't prevent recurrence. These changes add observability to prevent future silent stalls.

> [!WARNING]
> **Immediate action recommended:** Restart the backend process to acquire a fresh chain and lock a new anchor for the remaining trading day. The code changes below add diagnostics to prevent future undetected stalls.

## Proposed Changes

### ATM Decay Tracker (L1)

#### [MODIFY] [tracker.py](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/tracker.py)

Add `_capture_failure_streak` counter to track consecutive capture failures in [update()](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/tracker.py#132-186). When the counter exceeds a threshold (every 30 ticks ≈ 30 seconds), emit an `INFO`-level warning with the chain 0DTE contract count and spot, so operators can detect stall conditions.

Changes:
- Add `_capture_failure_streak: int = 0` to [__init__](file:///e:/US.market/Option_v3/l1_compute/tests/test_atm_decay_tracker.py#52-54)
- Reset to `0` in [_calculate_decay](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/tracker.py#234-313) on successful capture (when `self.anchor` becomes non-None)
- After [capture_anchor](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/runtime.py#319-323) in [update()](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/tracker.py#132-186), increment `_capture_failure_streak` if anchor is still None
- Log at `INFO` level every 30 consecutive failures

#### [MODIFY] [anchor.py](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/anchor.py)

Promote the `No 0DTE contracts` log from `DEBUG` to `INFO` level so operators can see why anchor capture fails in production logs.

#### [MODIFY] [runtime.py](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/runtime.py)

Reset `_capture_failure_streak` to `0` in [invalidate_tracker](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/runtime.py#184-200) and [reset_for_new_day](file:///e:/US.market/Option_v3/l1_compute/analysis/atm_decay/runtime.py#218-238).

---

### Tests

#### [MODIFY] [test_atm_decay_tracker.py](file:///e:/US.market/Option_v3/l1_compute/tests/test_atm_decay_tracker.py)

Add test: `test_update_logs_capture_stall_warning_after_threshold` — verifies that after N consecutive failed captures, the stall counter increments, and resets when anchor is finally captured.

## Verification Plan

### Automated Tests

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_tracker.py
powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_modular.py
```

### Manual Verification

1. After code changes are deployed and backend restarted, search the backend log for `capture stall` to confirm the new diagnostic message appears during any future capture failure streaks.

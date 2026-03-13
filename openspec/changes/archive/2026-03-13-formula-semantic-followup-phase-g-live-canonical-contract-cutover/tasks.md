## 1. L3 Canonical Source Mapping

- [x] 1.1 将 `ui_state.skew_dynamics` 的 live source 改为 `rr25_call_minus_put`
- [x] 1.2 保留 `skew_25d_valid` gate，移除 `skew_25d_normalized` 对 live UI state 的驱动
- [x] 1.3 将 `ui_state.tactical_triad.charm` 的 live source 改为 `net_charm_raw_sum`

## 2. Compatibility Rules

- [x] 2.1 保持 payload 顶层字段名和 schema 包络不变
- [x] 2.2 保留 `skew_25d_normalized` / `net_charm` 在 lower-layer compatibility / research path
- [x] 2.3 不新增新的前端页面字段

## 3. Verification

- [x] 3.1 更新 L3 `UIStateTracker` / reactor / presenter tests
- [x] 3.2 更新 L4 right-panel / skew / tactical-triad tests
- [x] 3.3 通过 `scripts/test/run_pytest.ps1 l3_assembly/tests/test_ui_state_tracker.py l3_assembly/tests/test_reactor.py`

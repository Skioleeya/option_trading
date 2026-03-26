# Tasks

## Implementation
- [x] 在 L3 `UIStateTracker` 通过 `micro_structure_state` 透传 `net_vanna_raw_sum`
- [x] 在 L4 Right Panel 新增 raw vanna 归一化与独立卡片
- [x] 保持 `dashboard_delta` 继续复用既有 `agent_g_data.micro_structure` contract

## Verification
- [x] `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_ui_state_tracker.py`
- [x] `npm --prefix l4_ui run test -- rightPanelModel rightPanelContract`
- [ ] 外部重启 backend 并抓取 live payload / `dashboard_delta`
- [ ] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

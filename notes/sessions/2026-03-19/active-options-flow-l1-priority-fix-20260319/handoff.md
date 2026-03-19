# Handoff

## Session Summary
- DateTime (ET): 2026-03-19 14:11:34 -04:00
- Goal: 修复 Active Options FLOW 长期零值问题，按 L1优先、去耦、模块化方案落地，并补齐显式降级与诊断链路。
- Outcome: 后端链路与合同变更已完成，目标后端回归通过；前端测试与在线验活受当前环境故障阻断，需在用户终端复核。

## What Changed
- Code / Docs Files:
  - `shared/services/active_options/input_adapter.py`
  - `shared/services/active_options/{__init__.py,constants.py,runtime_service.py,runtime_service_support.py}`
  - `app/loops/compute_loop.py`
  - `l3_assembly/events/{payload_events.py,active_options_contract.py}`
  - `l4_ui/src/types/dashboard.ts`
  - `l4_ui/src/components/right/{activeOptionsModel.ts,ActiveOptions.tsx}`
  - `scripts/ops/verify_active_options_hotfix.ps1`
  - `docs/SOP/{L3_OUTPUT_ASSEMBLY.md,L4_FRONTEND.md}`
  - `openspec/changes/refactor-dependency-20260319-active-options-compute-loop-single-source/{proposal.md,tasks.md}`
  - tests: `app/loops`, `shared/services/active_options`, `app/tests`, `l3_assembly/tests`, `l4_ui/src/components/__tests__`
- Runtime / Infra Changes:
  - `compute_loop` 改为在 L1 完成后发布 ActiveOptions 输入快照。
  - 引入 L1优先融合适配器（`computed_gamma/computed_vanna/computed_iv` 优先）。
  - ActiveOptions 行新增 `flow_signal_state/flow_signal_reason` 并透传到 L3/L4。
  - diagnostics 新增：`degraded_rows/live_rows/missing_gamma_rows/missing_turnover_rows`。
  - 验活脚本改为基于 `/debug/persistence_status.active_options` 判定健康。
- Commands Run:
  - `./scripts/test/run_pytest.ps1 app/loops/tests/test_compute_loop_gpu_dedup.py app/loops/tests/test_housekeeping_gpu_dedup.py shared/services/active_options/test_input_adapter.py shared/services/active_options/test_runtime_service.py app/tests/test_health_route_diagnostics.py l3_assembly/tests/test_payload_events.py l3_assembly/tests/test_reactor.py -q`
  - `npm --prefix l4_ui run test -- activeOptions.model activeOptions.render` (environment blocked)
  - `C:\Windows\System32\cmd.exe /c "D:\node\npm.cmd --prefix l4_ui run test -- activeOptions.model activeOptions.render"` (environment blocked)
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` (host error 8009001d)
  - `C:\Program Files\PowerShell\7\pwsh.exe -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - 后端目标回归：`78 passed in 5.23s`
  - `C:\Program Files\PowerShell\7\pwsh.exe -File scripts/validate_session.ps1 -Strict`：PASS
- Failed / Not Run:
  - 前端测试：Node CSPRNG 断言失败（环境问题，非用例断言失败）。
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`：宿主错误 `8009001d`（已改用 pwsh 通过）。

## Pending
- Must Do Next:
  - 在用户终端执行 `scripts/ops/verify_active_options_hotfix.ps1`。
  - 在可用 Node 环境执行 ActiveOptions 前端测试。
- Nice to Have:
  - 将 `flow_signal_reason` 分类统计接入统一告警面板。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 否（存在环境阻断导致的待补验证）
- DEBT-OWNER: Codex/User
- DEBT-DUE: 2026-03-20
- DEBT-RISK: 若不在稳定终端补测，线上仅有后端回归证据，缺失前端/在线验活闭环
- DEBT-NEW: 1
- DEBT-CLOSED: 0
- DEBT-DELTA: 1
- DEBT-JUSTIFICATION: 当前 shell 的 PowerShell/Node 运行时故障阻断在线验活与前端测试
- RUNTIME-ARTIFACT-EXEMPT: 无 runtime artifact 变更

## How To Continue
- Start Command:
  - `./scripts/ops/start_backend.ps1 -Foreground`
- Key Logs:
  - `logs/backend_runtime.current.log`
- First File To Read:
  - `shared/services/active_options/input_adapter.py`

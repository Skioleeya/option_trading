# Project State

## Snapshot
- DateTime (ET): 2026-03-19 14:11:34 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `d64eb98`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED` (local runtime shell intermittently impacted by WinError/crypto provider issues)
  - L0-L4 Pipeline: `DEGRADED` (frontend test runner blocked by Node CSPRNG assertion in this environment)

## Current Focus
- Primary Goal: 修复 Active Options FLOW 长期 `$0` 的输入链路与可观测性缺口（L1优先融合 + 显式降级）。
- Scope In:
  - `compute_loop` 改为 L1 后发布 ActiveOptions 输入快照。
  - shared 中立 `input_adapter`（L1优先、L0兜底、无效原因判定）。
  - ActiveOptions 行合同新增 `flow_signal_state/flow_signal_reason` 并贯通 L3/L4。
  - diagnostics 新增 `degraded/live/missing_gamma/missing_turnover` 计数。
  - 验活脚本改为依赖 `/debug/persistence_status.active_options` 指标。
- Scope Out:
  - LongPort/OS 网络栈本机故障根修（WinError 10106 / CSPRNG 断言）。

## What Changed (Latest Session)
- Files:
  - `shared/services/active_options/input_adapter.py`
  - `shared/services/active_options/__init__.py`
  - `shared/services/active_options/constants.py`
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/runtime_service_support.py`
  - `app/loops/compute_loop.py`
  - `l3_assembly/events/payload_events.py`
  - `l3_assembly/events/active_options_contract.py`
  - `l4_ui/src/types/dashboard.ts`
  - `l4_ui/src/components/right/activeOptionsModel.ts`
  - `l4_ui/src/components/right/ActiveOptions.tsx`
  - `scripts/ops/verify_active_options_hotfix.ps1`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `docs/SOP/L4_FRONTEND.md`
  - `openspec/changes/refactor-dependency-20260319-active-options-compute-loop-single-source/{proposal.md,tasks.md}`
  - tests: loops/runtime/health/L3/L4 增量更新
- Behavior:
  - ActiveOptions 输入从“L0 先发”切换为“L1 后发”，并通过中立适配器进行 L1优先字段融合。
  - FLOW 行支持显式 `LIVE|DEGRADED` 状态与原因透传，前端在任一降级行时显示 `DEGRADED`。
  - `/debug/persistence_status.active_options` 提供 live/degraded 与缺失信号分类统计。
  - `verify_active_options_hotfix.ps1` 由历史行质量判据切换为 debug 诊断判据。
- Verification:
  - `./scripts/test/run_pytest.ps1 ... -q`（loops + active_options + health + L3）=> `78 passed`
  - `C:\Program Files\PowerShell\7\pwsh.exe -File scripts/validate_session.ps1 -Strict` => `PASS`
  - 前端 `npm` 测试在当前环境被 Node CSPRNG 断言阻断（非用例断言失败）。

## Risks / Constraints
- Risk 1: 当前 shell `powershell` 宿主 `8009001d`，需用 `pwsh` 执行 strict。
- Risk 2: 当前环境 Node/CSPRNG 异常导致前端测试无法执行，需在用户终端复核。

## Next Action
- Immediate Next Step: 在用户稳定终端执行 `verify_active_options_hotfix.ps1` 与前端 ActiveOptions 测试，补在线证据。
- Owner: Codex/User

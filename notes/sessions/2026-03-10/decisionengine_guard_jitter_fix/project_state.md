# Project State

## Snapshot
- DateTime (ET): 2026-03-10 10:46:10 -04:00
- Branch: master
- Last Commit: 368c9b9
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 修复 DecisionEngine Guard 文案跳动（前端禁文案 + L2 VRP veto 滞回稳定）。
- Scope In:
  - `VRPVetoGuard` 从单阈值改为滞回状态机（entry/exit/hold）。
  - `GuardRailEngine` 提供 `reset_session()` 并由 `L2DecisionReactor.reset_session()` 调用。
  - `DecisionEngine` 停止渲染 `fused_signal.explanation`。
  - 更新 L2/L4 SOP 与对应测试。
- Scope Out:
  - 不改 `DecisionOutput` 字段结构。
  - 不改 L3 payload 合同结构。

## What Changed (Latest Session)
- Files:
  - l2_decision/guards/rail_engine.py
  - l2_decision/reactor.py
  - l2_decision/tests/test_reactor_and_guards.py
  - l4_ui/src/components/right/DecisionEngine.tsx
  - l4_ui/src/components/__tests__/decisionEngine.render.test.tsx
  - docs/SOP/L2_DECISION_ANALYSIS.md
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - VRP veto 默认参数：`entry=0.15`, `exit=0.13`, `min_hold_ticks=3`, `exit_confirm_ticks=2`。
  - 仅 `vrp > entry` 激活 veto；激活后需满足持有 + 退出确认才解除。
  - `reset_session()` 会清空 VRP veto 内部状态，避免跨日状态污染。
  - L4 不展示 `fused_signal.explanation`，Guard 文案不再出现在右侧面板。
- Verification:
  - `scripts/test/run_pytest.ps1 ... -k "vrp_veto or reset_session_calls_stateful_rule_reset"`: 5 passed。
  - `npm --prefix l4_ui run test -- src/components/__tests__/decisionEngine.render.test.tsx`: 2 passed（需提权执行）。
  - `scripts/test/run_pytest.ps1 l2_decision/tests/test_reactor_and_guards.py`: 9 failed, 47 passed（既有 Windows temp 目录权限问题，非本次改动引入）。

## Risks / Constraints
- Risk 1: 本机 `tempfile.TemporaryDirectory()` 清理权限异常会导致部分既有 L2 测试失败。
- Risk 2: L4 Vitest 在默认沙箱下会触发 `spawn EPERM`，需提权运行。

## Next Action
- Immediate Next Step: 关注 L2 全量测试环境权限问题（temp 目录）并在后续会话修复。
- Owner: Codex

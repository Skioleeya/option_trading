# Open Tasks

## Priority Queue
- [x] P0: DecisionEngine 前端禁文案（不再渲染 `fused_signal.explanation`）
  - Owner: Codex
  - Definition of Done: `DecisionEngine.tsx` 删除 explanation 渲染链路，组件测试断言文案不可见
  - Blocking: 无
- [x] P0: VRP Guard 滞回稳定化
  - Owner: Codex
  - Definition of Done: `VRPVetoGuard` 具备 entry/exit/hold 状态机，新增对应单测通过
  - Blocking: 无
- [x] P1: Guard 会话重置对齐
  - Owner: Codex
  - Definition of Done: `GuardRailEngine.reset_session()` 生效，`reactor.reset_session()` 通过公开接口调用
  - Blocking: 无
- [x] P1: SOP 同步（L2/L4）
  - Owner: Codex
  - Definition of Done: 文档明确 VRP 滞回规则与 L4 explanation 禁显规则
  - Blocking: 无

## Parking Lot
- [x] 记录既有环境问题：L2 全量测试在当前机器存在 Windows temp 目录权限异常（非本次改动引入）
- [x] 记录执行约束：L4 Vitest 在默认沙箱会触发 `spawn EPERM`，提权后目标用例可通过

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] DecisionEngine Guard 文案跳动修复（2026-03-10 10:46 ET）

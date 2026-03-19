# Open Tasks

## Priority Queue
- [x] P0: ActiveOptions FLOW L1优先融合 + compute_loop 发布时序切换
  - Owner: Codex
  - Definition of Done: ActiveOptions 输入由 L1 后快照发布，housekeeping 仅消费 shared snapshot，无跨层回流
  - Blocking: 无
- [x] P0: ActiveOptions 行合同与诊断扩展（`flow_signal_state/reason` + debug counters）
  - Owner: Codex
  - Definition of Done: L3/L4 合同同步，`/debug/persistence_status.active_options` 输出 `degraded/live/missing_*`
  - Blocking: 无
- [ ] P1: 在线验活与前端环境复核
  - Owner: User/Codex
  - Definition of Done: `verify_active_options_hotfix.ps1` 在用户终端 PASS，ActiveOptions 前端测试在可用 Node 环境完成
  - Blocking: 当前 shell 存在 WinError/CSPRNG 环境故障

## Parking Lot
- [ ] 评估将 `flow_signal_reason` 分桶接入统一告警面板。
- [ ] 评估将 `live_rows` 纳入会话健康 SLO。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 完成中立输入适配器 `input_adapter` 并接入 compute_loop（2026-03-19 ET）
- [x] 完成 FLOW 显式降级合同贯通与脚本诊断判据升级（2026-03-19 ET）

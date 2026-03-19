# Open Tasks

## Priority Queue
- [x] P0: 定位 ActiveOptions 无数据主因并交付独立诊断脚本
  - Owner: Codex
  - Definition of Done: 脚本可输出明确结论（过滤阈值/连接失败/链路空数据）及建议动作，并在当前仓库可执行
  - Blocking: `WinError 10106` 导致本 shell 无法访问本机 HTTP 端口，已降级为日志主证据
- [x] P1: 会话记录与元数据同步
  - Owner: Codex
  - Definition of Done: session-local 的 `project_state/open_tasks/handoff/meta` 完成更新
  - Blocking: 无
- [ ] P1: 在用户主机复跑诊断并回传结果
  - Owner: User/Codex
  - Definition of Done: 诊断脚本采集到 `/debug/persistence_status` + `/history` 证据并确认最终根因
  - Blocking: 需用户本机网络栈恢复（避免 `WinError 10106`）

## Parking Lot
- [ ] 若连接恢复后仍为空，增加链快照量化统计（volume/current_volume 分位）脚本。
- [ ] 若确认为阈值问题，补充最小阈值动态化建议（按交易时段）。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 独立诊断脚本 `scripts/diag/check_active_options_no_data_cause.py` 新增并本地可执行（2026-03-19 10:30 ET）
- [x] 脚本判定修复：避免将 HTTP 不可达时的 `None` 误判为 `0`（2026-03-19 10:29 ET）

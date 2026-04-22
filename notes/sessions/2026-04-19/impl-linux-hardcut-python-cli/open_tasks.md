# Open Tasks

## Priority Queue
- [x] P0: Linux 硬切替换运维入口，删除 `.ps1/.bat` 脚本
  - Owner: Codex
  - Definition of Done: `manage.py` 覆盖会话、校验、启动、EOD、边界扫描与测试入口；旧 Windows 脚本移除。
  - Blocking: None
- [x] P1: 更新门禁与规范文档为 Linux 命令链
  - Owner: Codex
  - Definition of Done: AGENTS/SOP/scripts README/启动文档/CI 均指向 `python3 manage.py ...`。
  - Blocking: None
- [x] P2: 迁移受影响测试调用并完成 strict 校验留痕
  - Owner: Codex
  - Definition of Done: EOD integration test 调用新 CLI；`validate-session --strict` 通过并写入 handoff/meta。
  - Blocking: 本机无 pytest，真实 pytest 结果需外部环境补充。

## Parking Lot
- [x] Item: 历史会话与 `openspec/changes/archive/*` 保持不改写。
- [x] Item: 非 archive 的历史 OpenSpec change 文本保持原样，仅更新主干规范入口。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added `manage.py` + `infra/ops_cli/*` Linux CLI surfaces (2026-04-19 12:05 ET)
- [x] Removed legacy Windows scripts under `scripts/` (2026-04-19 12:06 ET)
- [x] Updated CI/SOP/AGENTS/docs/test command references to Linux entrypoints (2026-04-19 12:10 ET)
- [x] Strict validation executed and passed (2026-04-19 12:15 ET)

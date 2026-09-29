# Project State (Index)

LAST_UPDATED: 2026-09-29
ACTIVE SESSION: notes/sessions/2026-09-29/startup-probe-fix-and-log-layout/
ARCHIVE: notes/context/archive/

## CURRENT_STATE

- 启动链路可用：`manage.py start-all` 端到端跑通（后端 `/health=200` + `L3-PAYLOAD` 实时 + 前端 HTTP-ready）。
- 日志布局已换为 `logs/<YYYY-MM-DD>/<service>/run-<NNN>.log`；旧的 `logs/*_runtime.current.log` 不再写入。
- 工作区存在**他会话未提交改动**，本会话未纳入、未评价。

## NEXT

- 见 `notes/sessions/2026-09-29/startup-probe-fix-and-log-layout/handoff.md::OPEN-RISKS`（含 3 项等 KAI 裁定）。

## Global Rules

- Session folders are immutable records; do not overwrite prior sessions.
- New substantive work must create a new session folder under notes/sessions/YYYY-MM-DD/<task-id>/.
- Session root holds at most three files: `handoff.md` (always) + `startup.md` / `project_state.md` as needed.
- Keep this index latest-state-only; push past summaries into notes/context/archive/.

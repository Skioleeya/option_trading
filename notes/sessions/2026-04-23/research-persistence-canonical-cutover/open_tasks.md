# Open Tasks

## Priority Queue
- [x] P0: 通过 `python manage.py validate-session --strict` 并记录 research canonical cutover strict 证据
  - Owner: `Codex`
  - Definition of Done: strict validate 全部绿灯，并把输出摘要写入 handoff
  - Blocking: session notes / context sync 必须完整；若 gate 失败需继续修根因
- [x] P1: 完成 research canonical cutover 的 `python manage.py start-all` Windows 主机健康验证
  - Owner: `Codex`
  - Definition of Done: `start-all` 成功启动且 `/health` 反映 research persistence healthy
  - Blocking: 可能存在端口或 `.pyd` 占用，需要最小化清理
- [x] P2: 同步 research canonical cutover 的 `notes/context/*` 与 session 记录
  - Owner: `Codex`
  - Definition of Done: context index / state / open_tasks / handoff 与本 session 一致
  - Blocking: 需等待 strict / start-all 结果定稿

## Parking Lot
- [x] 历史旧日 `research/raw|feature|label` 离线迁移已明确划出本 session 范围，后续如需执行需单开离线任务。
- [x] `l0_rust` / `shared_rust_services` 当前未使用 helper warning 已记录为非功能阻塞，不影响本次 owner hard-cut 交付。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] runtime research durable owner 切到 canonical 单文件模型（2026-04-23 09:13 ET）
- [x] 定向 research/history/health/EOD pytest 套件通过（2026-04-23 09:04 ET）
- [x] OpenSpec change `impl-20260423-research-persistence-canonical-cutover` 建立（2026-04-23 09:12 ET）
- [x] `python manage.py validate-session --strict` 通过（2026-04-23 09:22 ET）
- [x] `python manage.py start-all` + `/health` 验证 `research_persistence.healthy=true`（2026-04-23 09:20 ET）

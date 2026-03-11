# Project State

## Snapshot
- DateTime (ET): 2026-03-11 08:59:05 -04:00
- Branch: master
- Last Commit: fc174d4
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 重写仓库根文档 `启动步骤.md`，与实测成功启动方式一致（Redis + 后端 + 前端）。
- Scope In:
  - 以 probe-first + 按需启动 + strict->degraded 回退的顺序重写操作文档。
  - 提供可直接复制执行的 PowerShell 命令和最终验活步骤。
- Scope Out:
  - 不改动任何运行时代码/配置。
  - 不调整 L0-L4 契约字段与系统行为。

## What Changed (Latest Session)
- Files:
  - 启动步骤.md
- Behavior:
  - 启动文档改为“实测可用版”：先探测、按需启动 Redis、后端 strict 启动失败时回退 degraded、再启动前端、最后三端验活。
- Verification:
  - 文档命令基于本会话已成功拉起的实例流程整理（后端 `/health=200`、前端 `5173=200`、Redis `6380 LISTENING`）。

## Risks / Constraints
- Risk 1: 当前流程依赖本地环境已安装 Node/Python 与 `infra/bin/redis-server.exe`。
- Risk 2: strict 后端启动受 LongPort 连通性影响，部分环境需 degraded 回退。

## Next Action
- Immediate Next Step: 执行 strict session gate 并完成交付。
- Owner: Codex

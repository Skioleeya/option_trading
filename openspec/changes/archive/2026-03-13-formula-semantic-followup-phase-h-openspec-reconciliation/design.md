## Context

这一步只做治理文档对账，不再承担运行时修复。它的作用是把：

- 旧 family 的已实现历史
- 新 family 的 residual scope
- notes/context/session evidence

收敛成一个单一、可验证的状态。

## Decisions

1. 旧 A/B/D 任务按历史事实回填
2. 旧 `Phase C` 不删除，只标记 unfinished residual 由新 `Phase E` 接管
3. 父提案 closure 以新 follow-up family 为 residual closure 入口
4. reconciliation 必须在 strict validation 之前完成，避免 meta/tasks 与实际文件清单再次漂移

## Test Plan

- `openspec list`
- `scripts/validate_session.ps1 -Strict`
- 手工确认旧/new proposals 不再出现双重 active residual scope

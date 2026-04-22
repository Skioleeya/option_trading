## Why

旧 proposal family 已有实现历史，但 tasks / closure 状态仍然漂移：

- 旧 A/B/D tasks 没完全回填
- 旧 `Phase C` 仍显示未完成，却即将被新 `Phase E` 接管
- 旧父提案没有 residual handoff 说明

如果不做 reconciliation，旧/new proposals 会长期同时声明同一 scope。

## What Changes

1. 回填旧 A/B/D `tasks.md` 已完成项与验证证据
2. 在旧 `Phase C` 中显式标记 unfinished scope 由新 `Phase E` 接管
3. 更新旧父提案 tasks，记录 A/B/D 已完成历史与 C residual handoff
4. 将新 follow-up 父提案作为唯一 residual closure 入口

## Scope

- 旧/new OpenSpec proposal docs
- notes / handoff / meta 中的 residual state 对账
- 不引入新的 runtime 代码

## Parent

- `formula-semantic-followup-parent-governance`

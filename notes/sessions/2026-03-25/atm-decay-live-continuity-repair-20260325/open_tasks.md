# Open Tasks

## Priority Queue
- [x] P0: 运行 strict validation 并清零所有红门禁
  - Owner: Codex
  - Definition of Done: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` 通过
  - Blocking: 无
- [x] P1: 把 strict 输出与在线验证证据同步到 handoff/context
  - Owner: Codex
  - Definition of Done: session/context/meta 与 OpenSpec tasks 完整回填
  - Blocking: strict validation 结果
- [x] P2: 无
  - Owner: n/a
  - Definition of Done: n/a
  - Blocking: n/a

## Parking Lot
- [x] 无
- [x] 无

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] OpenSpec 变更骨架创建并落盘 (2026-03-25 10:09 ET)
- [x] ATM live continuity 与 history sanitizer 代码实现完成 (2026-03-25 10:13 ET)
- [x] 定向 pytest 与在线重启验证完成 (2026-03-25 10:18 ET)
- [x] `scripts/validate_session.ps1 -Strict` 通过 (2026-03-25 10:24 ET)

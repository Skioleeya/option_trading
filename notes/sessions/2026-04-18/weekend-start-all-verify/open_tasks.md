# Open Tasks

## Priority Queue
- [x] P0: 周末提权启动 `start_all.ps1` 并完成 L0-L4 可用性验收
  - Owner: Codex
  - Definition of Done: Redis/Backend/Frontend 启动成功，后端健康、L0-L3 指标正常、L4 WS 收到实时初始化 payload
  - Blocking: None
- [ ] P1: 如需“管理员上下文”复验，使用外部管理员 PowerShell 再跑一次 start_all
  - Owner: User/Ops
  - Definition of Done: 无 warning 的管理员态启动证据 + 同等链路指标
  - Blocking: 当前工具提权上下文不等价 UAC 管理员令牌
- [x] P2: 会话记录与 strict 留痕
  - Owner: Codex
  - Definition of Done: session/context 文件与 strict 验证命令记录完整
  - Blocking: None

## Parking Lot
- [x] Item: 非交易时段 research RTH 落盘为 0 的解释已记录
- [x] Item: WebSocket 端到端验证已执行

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `start_all.ps1` 启动成功（2026-04-18 08:28 ET）
- [x] L0-L4 链路诊断通过（2026-04-18 08:31 ET）
- [x] Strict validation 通过（2026-04-18 08:34 ET）

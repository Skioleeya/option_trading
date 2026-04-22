# Open Tasks

## Priority Queue
- [x] P0: GEX 阈值下调到 0.8B/4B（MMUSD 800/4000）
  - Owner: Codex
  - Definition of Done: `AgentG` 配置阈值更新并被后端加载生效
  - Blocking: None
- [x] P1: 边界回归测试补齐
  - Owner: Codex
  - Definition of Done: `classify_gex_regime` 边界与负值语义测试通过
  - Blocking: None
- [x] P1: 在线链路验收
  - Owner: Codex
  - Definition of Done: 最新 live 样本中 `net_gex >= 4000` 对应 `SUPER_PIN/SUPER PIN`
  - Blocking: None

## Parking Lot
- [ ] 观察盘中 SUPER PIN 触发占比，必要时二次微调 0.8B 档阈值

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 阈值重标定与在线验收完成 (2026-04-13 15:55 ET)

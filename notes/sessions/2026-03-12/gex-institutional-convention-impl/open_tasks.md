# Open Tasks

## Priority Queue
- [x] P0: GEX 统一为 1% spot-move MMUSD 口径，并维持 `net_gex=call-put` 兼容（Owner: Codex, Done: 2026-03-12 ET）
- [x] P0: 新增 `zero_gamma_level` 并拆分 `flip_level_cumulative`（Owner: Codex, Done: 2026-03-12 ET）
- [x] P1: Wall 规则切换为 spot 同侧优先 + 全局回退（Owner: Codex, Done: 2026-03-12 ET）
- [x] P1: L2 `gamma_flip` 改为优先 `spot vs zero_gamma_level`（Owner: Codex, Done: 2026-03-12 ET）
- [x] P1: L3 `gamma_flip_level` 对外指向 `zero_gamma_level` 且 DepthProfile 继续用 cumulative flip（Owner: Codex, Done: 2026-03-12 ET）
- [x] P1: 回归测试与 SOP 同步（Owner: Codex, Done: 2026-03-12 ET）

## Parking Lot
- [ ] 盘中复核 `zero_gamma_level` 在极端 skew 时的稳定性（Owner: Codex, Due: 2026-03-13）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 定向回归 `30 passed`（2026-03-12 ET）
- [x] 跨层回归 `80 passed`（2026-03-12 ET）
- [x] strict gate `scripts/validate_session.ps1 -Strict` 通过（2026-03-12 ET）

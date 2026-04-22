# Open Tasks

## Priority Queue
- [x] P0: 修复坏锚点连续腿饥饿时不会自愈重锁
  - Owner: Codex
  - Definition of Done: tracker 连续 `raw_pct_unavailable` 达阈值后自动 invalidation，并清除 persisted same-day anchor
  - Blocking: 无
- [x] P0: 清除 2026-03-25 当日 ATM anchor/history 并触发系统重判新 ATM
  - Owner: Codex
  - Definition of Done: 旧 `657` 锚点被清理，新的 `atm_20260325.json` 已落盘为重新捕获的锚点
  - Blocking: backend 重启
- [ ] P1: 观察新锚点后的首个有效 decay history 点是否恢复进入 `/api/atm-decay/history`. SUPERSEDED-BY: `2026-03-25/atm-decay-fresh-capture-relock-fix-20260325`
  - Owner: Codex
  - Definition of Done: `/api/atm-decay/history` `count > 0` 且出现新锚点下的首个有效时间点
  - Blocking: 实时 quote 两腿形成有效价格

## Parking Lot
- [x] 无
- [x] 无

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] tracker 连续腿饥饿自动 invalidation + persisted anchor 清理实现完成 (2026-03-25 10:39 ET)
- [x] housekeeping mandatory symbols 空集合显式同步完成 (2026-03-25 10:39 ET)
- [x] 新增/既有 pytest 回归通过 (2026-03-25 10:40 ET)
- [x] 2026-03-25 当日旧 ATM anchor/history 已清除并重启 backend (2026-03-25 10:43 ET)
- [x] 新锚点 `662` 已重新捕获并写回 `data/atm_decay/atm_20260325.json` (2026-03-25 10:44 ET)
- [x] `scripts/validate_session.ps1 -Strict` 通过，quality gate / openspec gate / debt gate 全绿 (2026-03-25 10:55 ET)

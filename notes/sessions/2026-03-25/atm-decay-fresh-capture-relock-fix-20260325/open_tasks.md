# Open Tasks

## Priority Queue
- [x] P0: 修复 startup retry 窗口在 pending restore anchor 存在时无法继续 fresh capture
  - Owner: Codex
  - Definition of Done: stale deferred anchor 被 discard 后，同次 startup bootstrap 继续 fresh-capture 新 same-day ATM
  - Blocking: 无
- [ ] P1: 继续观察 fresh-captured `661` 锚点后的首个有效 decay 点是否恢复进入 `/api/atm-decay/history`
  - Owner: Codex
  - Definition of Done: `/api/atm-decay/history` `count > 0`，并出现新 `661` anchor 下的首个有效时间点
  - Blocking: 需要锚定腿出现首个非零有效变动并通过 opening tick suppress
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
- [x] 识别 root cause：`bootstrap_intraday_anchor()` 被 `_pending_restore_anchor` 早退，startup retry 窗口无法处理 stale deferred anchor (2026-03-25 11:06 ET)
- [x] 实现 pending restore discard 后继续 fresh capture 的 startup bootstrap 修复 (2026-03-25 11:07 ET)
- [x] `l1_compute/tests/test_atm_decay_tracker.py` 与 `l1_compute/tests/test_atm_decay_modular.py` 回归通过 (2026-03-25 11:08 ET)
- [x] backend 重启后 stale `662` 被 discard，系统已 fresh-capture 新 `661` anchor (2026-03-25 11:08 ET)
- [x] `scripts/validate_session.ps1 -Strict` 通过，quality gate / openspec gate / debt gate 全绿 (2026-03-25 11:12 ET)

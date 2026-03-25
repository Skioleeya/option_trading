# Open Tasks

## Priority Queue
- [x] P0: 为 ATM fresh-capture stall 增加节流取证日志并补 L1 回归
  - Owner: Codex
  - Definition of Done: tracker 在 repeated capture failure 达阈值时输出 INFO forensic log，且成功锁锚后清零 streak
  - Blocking: 无
- [ ] P1: 使用新 stall diagnostics 继续观察并定位首个 post-lock ATM decay 样本为何没有进入 history/API
  - Owner: Codex
  - Definition of Done: 从运行日志可直接区分缺链、无同 strike C/P pair、opening tick suppress 或其它 post-lock 路径问题
  - Blocking: 需要下一轮在线观测窗口
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
- [x] 将 `No 0DTE contracts` 从 DEBUG 提升为 INFO，避免启动/盘中缺链被低级别日志吞没 (2026-03-25 11:51 ET)
- [x] 为 fresh-capture 失败引入 `_capture_failure_streak` 与阈值化 `capture stall` forensic log (2026-03-25 11:52 ET)
- [x] 新增 `test_update_logs_capture_stall_warning_after_threshold`，覆盖日志阈值触发与成功锁锚后的 streak reset (2026-03-25 11:53 ET)
- [x] `l1_compute/tests/test_atm_decay_tracker.py` 与 `l1_compute/tests/test_atm_decay_modular.py` 回归通过 (2026-03-25 11:54 ET)
- [x] `scripts/validate_session.ps1 -Strict` 通过，quality gate / openspec chain gate / debt gate 全绿 (2026-03-25 11:56 ET)

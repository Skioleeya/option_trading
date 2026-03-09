# Handoff

## Session Summary
- DateTime (ET): 2026-03-09 15:19:46 -04:00
- Goal: 修复后端重启后 ATM 锚点被重新开锁导致图表不连续的问题。
- Outcome: 已完成 deferred-restore 机制，确保 startup spot 不可用时不误开新锚，待首个有效 spot 严格校验后恢复持久化锚点。

## What Changed
- Code / Docs Files:
  - l1_compute/analysis/atm_decay/tracker.py
  - l1_compute/tests/test_atm_decay_modular.py
  - docs/SOP/L1_LOCAL_COMPUTATION.md
- Runtime / Infra Changes:
  - 新增 `pending_restore_anchor` 状态：启动 `spot` 不可用时暂存已校验 anchor。
  - `update()` 中新增 deferred 恢复路径：有效 `spot` 到来后执行距离校验并恢复锚点。
  - deferred 来源为 cold JSON 且 redis 可用时，恢复后自动回写 redis + 恢复序列。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId atm_anchor_deferred_restore -Timezone "Eastern Standard Time" -ParentSession "2026-03-09/wall_migration_restart_persistence"
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_modular.py l1_compute/tests/test_wall_migration_tracker.py

## Verification
- Passed:
  - scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_modular.py l1_compute/tests/test_wall_migration_tracker.py (12 passed)
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
- Failed / Not Run:
  - 未执行全量 pytest 与整链重启 E2E（本次为定向热修复）。

## Pending
- Must Do Next:
  - 在实盘重启流程验证 deferred 恢复命中（避免新开锚）。
- Nice to Have:
  - 增加 deferred-restore 运行时指标（命中次数、拒绝次数）。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本次范围内无新增未交付项；全量回归/E2E未纳入本次热修复范围
- DEBT-OWNER: Codex/User
- DEBT-DUE: 2026-03-11
- DEBT-RISK: 若不做全量重启链路回归，仍存在边缘恢复场景遗漏风险
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: DEBT-DELTA=0
- RUNTIME-ARTIFACT-EXEMPT: tmp/pytest_cache 为测试脚本缓存目录

## How To Continue
- Start Command:
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
- Key Logs:
  - [AtmDecayTracker] Deferred anchor restored / discarded
- First File To Read:
  - l1_compute/analysis/atm_decay/tracker.py

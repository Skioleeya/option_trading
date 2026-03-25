PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 11
BLOCKED_BY: refactor-dependency-20260325-atm-decay-anchor-recapture-repair

## Why

盘中在线验证表明：坏锚点自愈逻辑已经能清除失效 anchor，但 backend 重启后若存在 deferred restore anchor，`bootstrap_intraday_anchor()` 会因为 `_pending_restore_anchor` 非空而直接早退，导致 startup retry 窗口无法在同次启动内完成 fresh capture。

这会让 stale anchor 被 distance discard 后，系统错过最短重锁路径，延迟新 ATM 锚点恢复，进一步推迟首个有效 decay 点进入 history/API。

## What Changes

1. intraday startup bootstrap 在存在 pending restore anchor 时，必须先尝试 restore/discard。
2. 若 pending restore anchor 被丢弃，startup retry 窗口必须继续执行 fresh same-day capture，而不是直接返回。
3. 增加针对 “pending restore distance discard -> fresh recapture” 的 L1 回归测试。

## Hard Governance Prohibitions

- 禁止绕过严格 distance validation 直接恢复 stale anchor
- 禁止把 fresh capture 修复塞进 app 之外的非 L1 业务边界
- 禁止修改 L3/L4 payload 合同来掩盖 startup relock 缺失

## Scope

- 目标：`l1_compute/analysis/atm_decay/tracker.py`、`l1_compute/tests/test_atm_decay_tracker.py`、相关 SOP/session/OpenSpec 文档
- 非目标：ATM decay 数学公式改写、storage/API sanitizer 逻辑改版、前端图表行为调整

PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 9
BLOCKED_BY: none

## Why

盘前实盘检查暴露出两类 ATM decay 运行缺陷：

1. compute loop 在 `snapshot_version` 重复时整段跳过，导致 `AtmDecayTracker` 不续推 live tick；`/ws/dashboard` 的 `atm` 只会间歇更新，前端 TradingView 三条曲线无法持续增量绘制。
2. `atm_series_YYYYMMDD.jsonl` 与 Redis history 可混入未来时间戳和乱序点，`/api/atm-decay/history` 会把污染样本直接暴露给前端，破坏 cold boot 历史顺序和后续增量 append 判断。

需要一个最小行为修复：不改前端合同，不改 L1 ATM decay 数学本体，只修复 live 注入连续性与 history 暴露/恢复的时间序完整性。

## What Changes

1. 在 compute dedup 路径保持 L1/L2 skip，但允许 `AtmDecayTracker` 基于当前链快照续推 live ATM tick，并通过既有 L3 payload 合同广播。
2. 在 ATM decay storage/recovery 路径引入 history sanitizer：按 timestamp 排序、按 trade date 过滤、剔除未来样本与重复 timestamp，恢复到 Redis 前先净化。
3. `/api/atm-decay/history` 继续复用既有合同，但返回的 history 必须来自净化后的单调序列。
4. 扩展回归测试，覆盖 duplicate snapshot 下 ATM live continuity，以及 polluted history 的排序/过滤行为。

## Hard Governance Prohibitions

- 禁止为前端新增 replay-only/live-only 专用接口
- 禁止把 ATM decay 业务逻辑塞进 `app/` 以外的私有捷径或跨层私有访问
- 禁止破坏 `L0 -> L1 -> L2 -> L3 -> L4` 方向
- 禁止把 `timestamp/data_timestamp` 语义混成 broadcast time

## Scope

- 目标：`app/loops/*`、`l1_compute/analysis/atm_decay/*`、`app/routes/history.py`、相关测试、SOP、session/context 文档
- 非目标：ATM decay 数学公式重写、TradingView 视觉重构、L3 delta 编码协议重设计

## Parent

- `refactor-governance-20260317-l0-l2-data-path-remediation-chain`

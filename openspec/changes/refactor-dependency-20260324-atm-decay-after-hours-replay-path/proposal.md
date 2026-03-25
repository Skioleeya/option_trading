PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 8
BLOCKED_BY: none

## Why

盘后验证场景下，`AtmDecayTracker.update()` 按生产语义会停止产出新点，导致：

1. `/api/atm-decay/history` 在当天无 series 时保持空集。
2. `/ws/dashboard` 的 `atm` 持续为 `null`，前端 TradingView 只能 `-- PENDING`。
3. 测试无法区分“前端渲染坏了”与“盘后根本没有可消费 ATM 序列”。

需要一个 **test-only after-hours replay** 路径，把历史真实 ATM 序列映射到今天的标准链路中，验证保存、WS 和前端消费，不改变常规时段生产语义。

## What Changes

1. 在 `l1_compute.analysis.atm_decay` 内新增 after-hours replay provider，负责选择历史 source date、筛选非平台化窗口并重映射到当天 ET。
2. 通过 `AtmDecayTracker` 公共 API 在盘后测试态写入当天标准 ATM history/anchor，并在 `update()` / `compute_current_decay()` 中回放 tick。
3. 保持 `/api/atm-decay/history` 与 `/ws/dashboard` 合同不变，前端无感消费。
4. 扩展 60s 验证脚本，新增历史非平台化判定，允许浏览器级 replay 证据留痕。

## Hard Governance Prohibitions

- 禁止把 replay 逻辑放进 `app/` 私有跨层捷径
- 禁止默认开启盘后 replay
- 禁止修改前端为专用 replay 路径
- 禁止破坏 `data_timestamp/timestamp` 的 L0 源时间语义

## Scope

- 目标：`l1_compute/analysis/atm_decay/*`、`shared/config/*`、`scripts/test/atm_decay_frontend_live_validation_60s.py`、相关 SOP 与 session/context 文档
- 非目标：常规时段 live ATM 算法、L3 delta 编码策略、前端视觉设计重写

## Parent

- `refactor-governance-20260317-l0-l2-data-path-remediation-chain`

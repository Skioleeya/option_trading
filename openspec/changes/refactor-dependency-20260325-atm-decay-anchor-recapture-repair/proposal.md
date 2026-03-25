PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 10
BLOCKED_BY: refactor-dependency-20260325-atm-decay-live-continuity-and-history-sanitize

## Why

盘中排查显示 ATM decay 图表平台化的主因不是 L4 绘图，而是同日锚点锁定后，若锚定腿持续失去有效报价，tracker 会长期停在旧锚点上反复 `raw_pct_unavailable`，却不会主动失效并重判新 ATM。

同时，housekeeping 只会在锚点存在时同步 mandatory symbols；当锚点被清空后，旧 mandatory set 不会被显式清空，容易把失效腿继续粘在修复路径里。

## What Changes

1. ATM decay tracker 在同一锚点连续多次 `raw_pct_unavailable` 后必须显式失效当前锚点，并清除已持久化的当日锚点，允许系统重新锁定新的 ATM。
2. housekeeping 对 mandatory symbols 必须做全量同步：有锚点时同步锚点腿，无锚点时显式下发空集合，避免旧 mandatory 粘连。
3. 运维上允许清除当日 ATM anchor/history 以触发冷启动后的重新判锚。

## Hard Governance Prohibitions

- 禁止在 tracker 失效场景下引入静默吞错
- 禁止新增前端特判合同掩盖后端锚点失效
- 禁止跨层绕过 `option_chain_builder` 直接操纵 L0 私有状态

## Scope

- 目标：`l1_compute/analysis/atm_decay/*`、`app/loops/housekeeping_loop.py`、相关测试、SOP、session/context 文档
- 非目标：ATM decay 数学公式改写、TradingView 渲染风格调整、L3/L4 payload 改版

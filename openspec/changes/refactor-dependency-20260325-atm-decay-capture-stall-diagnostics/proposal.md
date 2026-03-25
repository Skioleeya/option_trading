PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 12
BLOCKED_BY: refactor-dependency-20260325-atm-decay-startup-bootstrap-fresh-capture

## Why

当前 `history/API` 仍未出现新锚点下的首个有效 ATM decay 点，在线排查需要能快速区分三类失败：

1. LongPort/quote connectivity 导致链输入残缺
2. 0DTE 链存在，但没有可交易同 strike 的 C/P pair
3. 选锚逻辑持续失败但日志信号太弱，无法从运行日志直接判断失败窗口长度

现状只在单次 capture 失败时输出零散日志，缺少节流后的 stall 取证汇总，导致盘中排查必须反复比对多处日志与冷文件。

## What Changes

1. 为 opening fresh-capture 增加失败 streak 计数与周期性 INFO 级取证日志。
2. 将 `No 0DTE contracts` 提升到 INFO，避免启动/盘中缺链被 DEBUG 级吞没。
3. 在 tracker invalidate/new-day reset/successful persist-anchor 时重置 capture failure streak，避免跨阶段污染诊断。
4. 增加 L1 回归测试，覆盖阈值触发日志与成功锁锚后的 streak 清零。

## Hard Governance Prohibitions

- 禁止把 stall diagnostics 塞进 `app/` 业务编排层
- 禁止修改 ATM decay 输出合同来传递诊断状态
- 禁止使用无界高频日志替代节流诊断

## Scope

- 目标：`l1_compute/analysis/atm_decay/{anchor,models,runtime,tracker}.py`、`l1_compute/tests/test_atm_decay_tracker.py`、`docs/SOP/L1_LOCAL_COMPUTATION.md`、session/OpenSpec 文档
- 非目标：LongPort SDK 网络重试策略、前端图表渲染、ATM decay 数学公式与存储合同改版

# Project State

## Snapshot
- DateTime (ET): 2026-04-13 15:31:53 -04:00
- Branch: chore/sync-all-local-changes-20260313
- Last Commit: 00a88fd
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 修复 MICRO STATS 中 NET GEX 状态标签未生效的根因，硬切禁止 fallback/兼容。
- Scope In:
  - L3 `gex_regime` 解析契约严格化与 fail-fast
  - 移除 `MicroStatsPresenterV2` 的 ImportError fallback
  - NET GEX 状态映射严格命中 + 回归测试 + SOP 同步
- Scope Out:
  - 不改动 L1 计算逻辑与阈值定义
  - 不改动前端组件布局

## What Changed (Latest Session)
- Files:
  - l3_assembly/assembly/gex_regime_contract.py
  - l3_assembly/assembly/ui_state_tracker.py
  - l3_assembly/presenters/micro_stats.py
  - l3_assembly/presenters/ui/micro_stats/presenter.py
  - app/tests/test_ui_state_tracker_gex_regime.py
  - app/tests/test_micro_stats_net_gex_contract.py
  - docs/SOP/L3_OUTPUT_ASSEMBLY.md
- Behavior:
  - `UIStateTracker` 对对象路径里的字符串型 `gex_regime` 不再误降级为 `NEUTRAL`。
  - 未知 `gex_regime` 现在直接抛错（fail-fast），不再静默兜底。
  - `MicroStatsPresenterV2` 删除 ImportError fallback，NET GEX 映射未知状态直接报错。
- Verification:
  - `scripts/test/run_pytest.ps1 app/tests/test_ui_state_tracker_gex_regime.py app/tests/test_micro_stats_net_gex_contract.py` -> 8 passed

## Risks / Constraints
- Risk 1: 当前未连接实盘后端，未做在线 payload 验证，仅完成离线回归。
- Risk 2: 未知 `gex_regime` 现在会触发 fail-fast，依赖上游合同稳定输出四态枚举。

## Next Action
- Immediate Next Step: 运行 strict gate，并在通过后同步 context 指针与 handoff。
- Owner: Codex

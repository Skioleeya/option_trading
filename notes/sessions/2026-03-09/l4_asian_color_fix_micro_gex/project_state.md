# Project State

## Snapshot
- DateTime (ET): 2026-03-09 15:35:25 -04:00
- Branch: master
- Last Commit: f2268d2
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 将 MicroStats 与 GEX 状态栏修正为亚洲盘语义（红涨绿跌）并统一状态映射管理。
- Scope In:
  - `gexStatus.ts` 增加亚洲语义状态映射输出。
  - `GexStatusBar.tsx` 移除反向硬编码配色，改为使用状态映射模块。
  - `microStatsTheme.ts` 强化 badge 归一化和方向推断，修正非亚洲配色令牌。
  - 更新对应前端单测与 L4 SOP。
- Scope Out:
  - 不改后端 payload 字段与 L3/L2 逻辑。
  - 不调整组件布局结构。

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/center/gexStatus.ts
  - l4_ui/src/components/center/GexStatusBar.tsx
  - l4_ui/src/components/center/__tests__/gexStatus.test.ts
  - l4_ui/src/components/left/microStatsTheme.ts
  - l4_ui/src/components/left/MicroStats.tsx
  - l4_ui/src/components/left/__tests__/microStatsTheme.test.ts
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - NET GEX：`>0` 显示红（BULLISH），`<0` 显示绿（BEARISH），`0/null` 中性灰。
  - Call/Put Wall：颜色语义修正为亚洲风格（Call 绿、Put 红），并由 `gexStatus.ts` 统一输出样式 token。
  - MicroStats：补充 `bull/bear` badge token 及 label 方向推断，避免 badge 缺失时出现反向语义。
- Verification:
  - `scripts/test/run_pytest.ps1 l1_compute/tests/test_wall_migration_tracker.py` 通过（5 passed）。
  - 前端 vitest 当前环境存在既有问题（No test suite / integration 初始化异常），未能用作有效回归信号。

## Risks / Constraints
- Risk 1: 前端 vitest 环境当前存在全局收集异常，影响本次组件级单测执行。
- Risk 2: 未完成浏览器端截图式验收（需用户重载页面确认视觉结果）。

## Next Action
- Immediate Next Step: 执行 strict gate 后，请用户重启后端并刷新前端确认配色与状态语义。
- Owner: Codex/User

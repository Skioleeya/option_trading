# Project State

## Snapshot
- DateTime (ET): 2026-03-11 11:09:05 -04:00
- Branch: master
- Last Commit: fc174d4
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: WALL DYN 强制一致性修复（Micro Stats 与 Wall Migration 语义/方向一致，保持红涨绿跌）。
- Scope In:
  - L3 Micro Stats WALL DYN 分类、映射、debounce 语义修复
  - L3 跨模块一致性回归补测
  - SOP 同步（L3）
- Scope Out:
  - 不改 L0/L1/L2/L4 对外接口
  - 不改 Rust 运行时路径

## What Changed (Latest Session)
- Files:
  - l3_assembly/presenters/ui/micro_stats/{thresholds.py,wall_dynamics.py,palette.py,mappings.py,presenter.py}
  - l3_assembly/tests/{test_micro_stats_wall_dynamics.py,test_assembly.py}
  - docs/SOP/L3_OUTPUT_ASSEMBLY.md
- Behavior:
  - `RETREATING_RESISTANCE` -> `RETREAT ↑`（红），`RETREATING_SUPPORT` -> `RETREAT ↓`（绿）。
  - `COLLAPSE` 仍严格门控：put retreat + SHORT_GAMMA + high hedge_flow_intensity。
  - Debounce 从“全非紧急态”收敛为仅 `PINCH/SIEGE`，`BREACH/RETREAT ↑/RETREAT ↓/COLLAPSE` 同 tick 生效。
- Verification:
  - 必测 pytest: 67 passed
  - 关联 L4: microStatsTheme vitest 1 file / 4 tests passed
  - strict gate: passed
  - 运行时最小复现：修复后同 tick `RETREAT ↓` 对齐（Micro Stats 与 Wall Migration）

## Risks / Constraints
- Risk 1: `RETREAT` 双侧同时出现时保留兼容键 `RETREAT`（方向中性）。
- Risk 2: `wall_collapse_flow_intensity_threshold` 仍需实盘校准（非本次阻断项）。

## Next Action
- Immediate Next Step: 进入阈值校准观测阶段（非阻断）。
- Owner: Codex

# Open Tasks

## Priority Queue
- [x] P0: 修复 `check-layer-boundaries` 在无 git 环境下 fallback 误报
  - Owner: Codex
  - Definition of Done: fallback 仅扫描允许目录并排除 `.venv/node_modules/dist/target/tmp/logs/data`；命令可通过。
  - Blocking: None
- [x] P1: 拆分 `dashboardStore.ts` 并保持行为等价
  - Owner: Codex
  - Definition of Done: `dashboardStore.ts` <= 400 行；导出兼容；`helpers/merge/selectors` 模块化完成。
  - Blocking: None
- [x] P2: 完成首波会话验证与留痕
  - Owner: Codex
  - Definition of Done: 更新 session/context 文档与 `meta.yaml`，并执行 `python3 manage.py validate-session --strict`。
  - Blocking: 前端 vitest 依赖缺失导致单测项只能记录失败，不阻断 strict gate。

## Parking Lot
- [x] Item: 本波不处理 `AtmDecayChart.tsx`（486 行）。
- [x] Item: 本波不处理 `l3_assembly/assembly/ui_state_tracker.py`（401 行）。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Layer boundary fallback filtering stabilized (2026-04-19 13:26 ET)
- [x] `dashboardStore` split into `helpers/merge/selectors` modules (2026-04-19 13:27 ET)
- [x] `dashboardStore.ts` reduced to 192 lines (2026-04-19 13:27 ET)

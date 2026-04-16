# Project State

## Snapshot
- DateTime (ET): 2026-04-16 18:31:37 -04:00
- Branch: chore/sync-all-local-changes-20260313
- Last Commit: e91cff0
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK` (L4 全量测试恢复绿灯)

## Current Focus
- Primary Goal: 修复 ActiveOptions 渲染回归并恢复 L4 全量测试通过。
- Scope In:
  - `activeOptionsModel` 槽位去重补位
  - `activeOptions.render` 测试合同对齐
  - L4 全量回归验证
  - Wave5 OpenSpec + L4 SOP 同步
- Scope Out:
  - 上游 L0-L3 排序策略
  - ActiveOptions 视觉主题重构

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/right/activeOptionsModel.ts
  - l4_ui/src/components/__tests__/activeOptions.render.test.tsx
  - docs/SOP/L4_FRONTEND.md
  - openspec/changes/impl-20260416-mm-rust-cutover-wave5-l4-activeoptions-regression/*
- Behavior:
  - `slot_index` 在重复/越界场景下会被归一到唯一 1..5 槽位，避免重复 DOM key。
  - 前端继续保持后端输入顺序，不做本地 VOL 二次排序。
- Verification:
  - ActiveOptions 定向 model/render 测试通过。
  - `l4_ui` 全量测试通过（38 files, 183 tests）。

## Risks / Constraints
- Risk 1: 仍有大量并行未提交改动，本会话仅覆盖 Wave5 指定文件。
- Risk 2: 真实后端若长期输出异常 `slot_index`，前端会归一显示，但应继续追踪上游数据质量。

## Next Action
- Immediate Next Step: 将 duplicate/out-of-range `slot_index` 场景补充到 model 专项测试集。
- Owner: Codex

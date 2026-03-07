# Project State

## Snapshot
- DateTime (ET): 2026-03-07 08:47:12 -05:00
- Branch: master
- Last Commit: c7389f3
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED` (LongPort 网络可达性受限)
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 完整更新 `docs/SOP` 六份核心文档（架构图 + 文本规范）并形成可交接版本。
- Scope In:
  - 重写 `SYSTEM_OVERVIEW` 与 L0/L1/L2/L3/L4 分层 SOP。
  - 补齐架构图、依赖边界、契约语义、启动/验证章节。
  - 完成会话级验证与记录。
- Scope Out:
  - 不改动运行时代码逻辑，仅文档更新。

## What Changed (Latest Session)
- Files:
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `docs/SOP/L4_FRONTEND.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-07/0845_p0_sop_full_refresh_mod/project_state.md`
  - `notes/sessions/2026-03-07/0845_p0_sop_full_refresh_mod/open_tasks.md`
  - `notes/sessions/2026-03-07/0845_p0_sop_full_refresh_mod/handoff.md`
  - `notes/sessions/2026-03-07/0845_p0_sop_full_refresh_mod/meta.yaml`
- Behavior:
  - SOP 结构从历史补丁式条目改为统一模板，六层文档均含图示、契约、边界与验证节。
  - 明确了单向依赖硬约束与降级启动语义，形成统一可查规范。
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py`

## Risks / Constraints
- Risk 1: 本次是文档全面重写，若团队仍引用旧段落锚点，需同步更新引用位置。
- Risk 2: 当前仓库存在其他未提交运行时改动；本会话只处理 SOP 文档与会话记录。

## Next Action
- Immediate Next Step: 由开发与量化团队按新 SOP 清单做一次跨层 walkthrough，确认术语与执行口径一致。
- Owner: Codex

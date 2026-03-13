# Project State

## Snapshot
- DateTime (ET): 2026-03-12 12:45:32 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 审计仓库期权指标与 2024-2026 学术论文公式、单位、符号和阈值的一致性，并输出两份 Markdown 报告。
- Scope In:
  - L1/L2/Shared-ActiveOptions 指标实现定位与口径核对
  - 2024-2026 一手来源论文检索与摘录
  - `docs/OPTION_PAPER_FORMULA_AUDIT_2024_2026.md`
  - `docs/OPTION_PAPER_FORMULA_SOURCEBOOK_2024_2026.md`
  - session/context 同步与 strict gate
- Scope Out:
  - 任何 L0-L4/app 运行时代码修改
  - 任何阈值/合约/字段的线上行为修复
  - 旧 session 的追溯性重写

## What Changed (Latest Session)
- Files:
  - `docs/OPTION_PAPER_FORMULA_AUDIT_2024_2026.md`
  - `docs/OPTION_PAPER_FORMULA_SOURCEBOOK_2024_2026.md`
  - `notes/sessions/2026-03-12/option-paper-formula-audit-2024-2026/project_state.md`
  - `notes/sessions/2026-03-12/option-paper-formula-audit-2024-2026/open_tasks.md`
  - `notes/sessions/2026-03-12/option-paper-formula-audit-2024-2026/handoff.md`
  - `notes/sessions/2026-03-12/option-paper-formula-audit-2024-2026/meta.yaml`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Behavior:
  - 无运行时行为修改；新增两份研究/审计文档，并明确哪些指标与论文一致、哪些仅是工程 proxy、哪些阈值无论文依据。
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> passed

## Risks / Constraints
- Risk 1: 当前联网环境无法直接渲染 Google 结果页，因此本次采用等价的 Google 风格 `site:` 查询词通过内置 web 搜索工具执行。
- Risk 2: 多数近期论文讨论的是真实 dealer/OMM inventory 或 demand pressure；仓库公开数据只支持 `OI-based proxy` 审计。

## Next Action
- Immediate Next Step: 同步 handoff/meta/context 并跑 strict validation；若失败则按首个 failing gate 修复后重跑。
- Owner: Codex

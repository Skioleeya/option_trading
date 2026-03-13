# Project State

## Snapshot
- DateTime (ET): 2026-03-12 12:56:01 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 获取 LongPort 官方 `llms.txt` 的有效字段并整理为仓库内可直接使用的 Markdown 文档。
- Scope In:
  - 抓取 `https://open.longportapp.com/llms.txt`
  - 提取平台能力、接入前提、限频、市场覆盖、交易支持与文档索引
  - 产出 `docs/LONGPORT_LLMS_EFFECTIVE_FIELDS.md`
  - session/context 同步与 strict gate
- Scope Out:
  - 任何运行时代码修改
  - 任何 LongPort API 集成实现变更
  - 对 `quote/trade` 细分页面做字段级深挖

## What Changed (Latest Session)
- Files:
  - `docs/LONGPORT_LLMS_EFFECTIVE_FIELDS.md`
  - `notes/sessions/2026-03-12/longport-llms-fields-doc/project_state.md`
  - `notes/sessions/2026-03-12/longport-llms-fields-doc/open_tasks.md`
  - `notes/sessions/2026-03-12/longport-llms-fields-doc/handoff.md`
  - `notes/sessions/2026-03-12/longport-llms-fields-doc/meta.yaml`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Behavior:
  - 无运行时行为修改；新增一份 LongPort `llms.txt` 有效字段提取文档，按本仓库接入需求重组官方摘要与文档索引。
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> passed

## Risks / Constraints
- Risk 1: `llms.txt` 本身是摘要与导航，不是完整 API 字段契约；更细字段仍需下钻各 `docs/...md` 页面。
- Risk 2: 当前文档仅提取“有效字段”，不会替代官方接口文档。

## Next Action
- Immediate Next Step: 同步 handoff/meta/context 并跑 strict validation；若失败则修复后重跑。
- Owner: Codex

# Project State

## Snapshot
- DateTime (ET): 2026-03-12 12:15:49 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 产出一份可检索的 IV 指标索引文档，明确当前仓库哪些指标直接或间接基于 IV 计算。
- Scope In:
  - L1/L2/L3 以及 shared ActiveOptions/VRP 相关 IV 指标清单。
  - 指标级别的公式摘要和来源文件定位。
  - 当前 session 与 context 指针同步。
- Scope Out:
  - 任何运行时逻辑、阈值或合约变更。
  - 历史 session 文档的追溯性改写。

## What Changed (Latest Session)
- Files:
  - `docs/IV_METRICS_MAP.md`
  - `notes/sessions/2026-03-12/iv-metrics-doc/project_state.md`
  - `notes/sessions/2026-03-12/iv-metrics-doc/open_tasks.md`
  - `notes/sessions/2026-03-12/iv-metrics-doc/handoff.md`
  - `notes/sessions/2026-03-12/iv-metrics-doc/meta.yaml`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Behavior:
  - 无运行时行为变化；新增一份 IV 指标索引文档，区分直接依赖和间接依赖 IV 的指标。
- Verification:
  - `scripts/validate_session.ps1 -Strict` -> passed

## Risks / Constraints
- Risk 1: 该文档是“当前实现快照”，若后续新增 IV 指标或调整字段名，需要同步维护。
- Risk 2: 若研究侧继续沿用旧 `institutional` 措辞，可能和当前 `OI-based proxy` 语义产生理解偏差。

## Next Action
- Immediate Next Step: 如后续新增 IV 指标或切换 GEX 主口径，需同步更新该索引文档。
- Owner: Codex

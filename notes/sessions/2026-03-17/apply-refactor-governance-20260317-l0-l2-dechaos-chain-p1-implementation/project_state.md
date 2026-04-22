# Project State

## Snapshot
- DateTime (ET): 2026-03-17 18:49 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `a3fa027`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 落地 L0-L2 去混乱父提案与两条 P1 子提案（AgentG + IVBaselineSync）。
- Scope In:
  - OpenSpec 父提案 + 子提案 A/B 文档四件套
  - `AgentG` 决策管线模块拆分
  - `IVBaselineSync` 流程扁平化与解析器抽取
  - 目标回归测试与质量/边界/strict 门禁
  - `/opsx-archive` 归档与启动文档修订
- Scope Out:
  - 新增 L3/L4 行为变更
  - schema/契约改名

## What Changed (Latest Session)
- Files:
  - `openspec/changes/archive/2026-03-17-refactor-governance-20260317-l0-l2-dechaos-chain/*`
  - `openspec/changes/archive/2026-03-17-refactor-bloat-20260317-l2-agentg-decision-pipeline-split/*`
  - `openspec/changes/archive/2026-03-17-refactor-nesting-20260317-l0-ivbaselinesync-flow-flattening/*`
  - `l2_decision/agents/agent_g.py`
  - `l2_decision/agents/services/agent_g_decision_support.py`
  - `l0_ingest/feeds/iv_baseline_sync.py`
  - `l0_ingest/feeds/iv_baseline_sync_support.py`
  - `l2_decision/tests/test_agent_g_decision_support.py`
  - `l0_ingest/tests/test_iv_baseline_sync_support.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
  - `启动步骤.md`
- Behavior:
  - AgentG 决策主流程由大函数改为编排+小函数，支持模块化 helper。
  - IVBaselineSync warm_up/staggered 由深嵌套改为编排+批处理 helper。
  - 对外接口保持不变（`AgentG.decide`、`IVBaselineSync` 公共入口）。
  - 后端启动文档补充后台/前台两种方式及日志追踪方法。
- Verification:
  - `check_layer_boundaries.ps1`: pass
  - `check_quality_gates.py` (targeted meta): pass
  - `validate_session.ps1 -Strict`: pass（含归档后复跑）
  - 目标 pytest: pass

## Quant (Before -> After)
- AgentG `_decide_impl`: len `362 -> 131`, CC `107 -> 40`, nesting `9 -> 1`
- IVBaselineSync `warm_up`: len `97 -> 34`, CC `28 -> 7`, nesting `9 -> 2`
- IVBaselineSync `_staggered_sync`: len `96 -> 17`, CC `20 -> 2`, nesting `9 -> 1`

## Risks / Constraints
- Risk 1: 目前仅完成 P1 第一阶段“显著降复杂度”，第二阶段硬阈值仍需后续收口。
- Risk 2: 主机环境存在 `WinError 10106` 历史问题，若复发会影响网络类回归。
- Risk 3: 本机 Node/CSPRNG 异常导致 `openspec` CLI 无法执行，已用等价文件归档完成流程。

## Next Action
- Immediate Next Step: 进入 Stage-2 硬阈值收口（AgentG/IVBaselineSync）。
- Owner: Codex

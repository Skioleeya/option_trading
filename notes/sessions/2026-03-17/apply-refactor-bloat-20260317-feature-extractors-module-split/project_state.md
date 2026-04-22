# Project State

## Snapshot
- DateTime (ET): 2026-03-17 13:29:01 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `06be8f2`
- Environment:
  - Market: `UNKNOWN`
  - Data Feed: `UNKNOWN`
  - L0-L4 Pipeline: `UNKNOWN`

## Current Focus
- Primary Goal: 落地第三子提案（`refactor-bloat-20260317-feature-extractors-module-split`）并完成 `extractors.py` 主题化拆分。
- Scope In:
  - `l2_decision/feature_store/extractors.py`
  - `l2_decision/feature_store/extractors_common.py`
  - `l2_decision/feature_store/extractors_flow.py`
  - `l2_decision/feature_store/extractors_skew.py`
  - `l2_decision/feature_store/extractors_volatility.py`
  - `l2_decision/feature_store/extractors_registry.py`
  - `openspec/changes/refactor-bloat-20260317-feature-extractors-module-split/{design.md,tasks.md}`
- Scope Out:
  - L0/L1 runtime 变更
  - 新 feature 语义引入（本次仅结构拆分）

## What Changed (Latest Session)
- Files:
  - 以 `flow/skew/volatility/common/registry` 五模块拆分 `extractors.py`
  - `extractors.py` 退化为兼容入口并保留对外注册函数
  - 更新 bloat 子提案设计与任务证据
- Behavior:
  - `build_default_extractors` / `reset_all_default_extractors` 对外合同保持不变
  - 现有测试依赖的 `_TurnoverVelocityExtractor` / `_MaxImpactExtractor` 兼容导出保留
- Verification:
  - `python -m py_compile ...` PASS
  - pytest 仍受主机 `WinError 10106` 阻塞

## Risks / Constraints
- Risk 1: 主机 Python `asyncio` 初始化失败（WinError 10106）阻塞 pytest。
- Risk 2: 当前工作区含跨会话未提交变更，需统一提交策略管理。

## Next Action
- Immediate Next Step: 完成 session/context 收口并执行 strict validate。
- Owner: Codex

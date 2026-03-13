# Project State

## Snapshot
- DateTime (ET): 2026-03-12 12:00:12 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 将当前生效的 GEX/Wall/Flip 文案统一为 `OI-based proxy` 语义，去除会被误解为 dealer inventory 真值的措辞。
- Scope In:
  - 当前生效 SOP 文档中的 GEX/flip 语义声明。
  - 当前代码注释、类型字段说明中的 GEX 语义说明。
  - `example.py` 的定位说明。
  - 当前 context/session 指针与 handoff 文案同步。
- Scope Out:
  - 历史归档 session 与 archive 文档的追溯性改写。
  - GEX/Wall/Flip 运行时逻辑和测试行为变更。

## What Changed (Latest Session)
- Files:
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
  - `l1_compute/analysis/greeks_engine.py`
  - `l1_compute/analysis/bsm_fast.py`
  - `l1_compute/analysis/bsm.py`
  - `l1_compute/output/enriched_snapshot.py`
  - `example.py`
- Behavior:
  - 明确当前系统的 GEX/Wall/Flip 为 `OI-based proxy` 语义。
  - 禁止将 Longbridge 公开字段条件下的 GEX 文案表述为 dealer inventory 真值。
  - 将 `example.py` 标记为外部库存重建示例而非仓库生产主口径。
- Verification:
  - `scripts/validate_session.ps1 -Strict` -> passed

## Risks / Constraints
- Risk 1: 历史归档文档仍保留旧措辞，可能在全文检索时继续出现“institutional”字样。
- Risk 2: 若后续接入具备逐笔 `customer/dealer` 与 `open_close` 标签的新数据源，需再次同步 SOP 和对外文案。

## Next Action
- Immediate Next Step: 如后续接入含 `customer/dealer/open_close` 标签的新数据源，再评估是否从 OI-based proxy 升级为 inventory-based 主口径。
- Owner: Codex

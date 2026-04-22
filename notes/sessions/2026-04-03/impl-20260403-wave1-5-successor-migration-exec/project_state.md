# Project State

## Snapshot
- DateTime (ET): 2026-04-03 10:08:12 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `aa3efd7`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 执行 Wave 1.5，落地两个 audit 的 successor migration proposal（`l1-wall-context-rust` + `l2-attention-fusion-rust`）。
- Scope In:
  - `shared_rust_services/src/fusion.rs`
  - `shared_rust_services/src/microstructure.rs`
  - `shared_rust_services/src/lib.rs`
  - `l2_decision/fusion/attention_fusion.py`
  - `l2_decision/README.md`
  - `l1_compute/microstructure/wall_context_builder.py`
  - `l2_decision/tests/test_attention_fusion_rust_bridge.py`
  - `l1_compute/tests/test_wall_context_builder_rust_bridge.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
  - `openspec/changes/impl-20260403-l1-wall-context-rust/*`
  - `openspec/changes/impl-20260403-l2-attention-fusion-rust/*`
- Scope Out:
  - 无关 L0/L3/L4 运行时改动
  - 无关策略语义重设计

## What Changed (Latest Session)
- Files:
  - Added `shared_rust_services/src/fusion.rs`
  - Updated `shared_rust_services/src/microstructure.rs`
  - Updated `shared_rust_services/src/lib.rs`
  - Updated `l2_decision/fusion/attention_fusion.py`
  - Updated `l1_compute/microstructure/wall_context_builder.py`
  - Added `l2_decision/tests/test_attention_fusion_rust_bridge.py`
  - Added `l1_compute/tests/test_wall_context_builder_rust_bridge.py`
  - Updated `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - Updated `docs/SOP/L2_DECISION_ANALYSIS.md`
  - Updated `openspec/changes/impl-20260403-l1-wall-context-rust/{proposal.md,tasks.md}`
  - Updated `openspec/changes/impl-20260403-l2-attention-fusion-rust/{proposal.md,tasks.md}`
- Behavior:
  - `attention_fusion.py` 移除 NumPy softmax/dot 运行时计算，改为 Rust owner `compute_attention_fused`。
  - `wall_context_builder.py` 移除 Python 侧数值清洗/循环 marshalling，改为 Rust owner 直接接管 chain snapshot 解析与计算。
  - `RecordBatch` 路径改为 Arrow 列直传 Rust（不经 Python `to_pylist()`/NumPy 算术）。
  - `FusedDecision/DecisionOutput/DecisionAuditEntry` 的 `fusion_weights` 在 attention mode 保持连续。
  - 新增 `DecisionOutput.data["fused_signal"]` 契约断言，锁定 L2->L3/L4 下游兼容面。
- Verification:
  - Rust build + artifact replacement succeeded.
  - Targeted L1/L2 tests passed.
  - Strict session validation passed.

## Risks / Constraints
- Risk 1: 仓库有历史未清理改动（logs/tmp 等），本会话未回滚。
- Risk 2: `shared_rust/services.pyd` 替换依赖目标文件无外部锁（本次替换成功）。

## Next Action
- Immediate Next Step: handoff complete.
- Owner: Codex

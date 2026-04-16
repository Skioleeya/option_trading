# Project State

## Snapshot
- DateTime (ET): 2026-04-16 18:01:06 -04:00
- Branch: chore/sync-all-local-changes-20260313
- Last Commit: e91cff0
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED` (Wave3 complete, end-to-end UI consumption session pending)

## Current Focus
- Primary Goal: Complete Wave3 L3 assembly contract for institutional MM flow payload/delta surfaces.
- Scope In:
  - `FrozenPayload` 增加稳定 `mm_flow` 输出口径
  - delta encoder 增量变更中增加 `agent_g_data.mm_flow`
  - L3 专项合同测试 + OpenSpec Wave3 + SOP 同步
- Scope Out:
  - L4 组件消费与展示映射
  - 新增跨层计算逻辑

## What Changed (Latest Session)
- Files:
  - l3_assembly/events/payload_events.py
  - l3_assembly/assembly/delta_encoder.py
  - l3_assembly/events/test_payload_mm_flow_contract.py
  - l3_assembly/assembly/test_delta_encoder_mm_flow.py
  - docs/SOP/L3_OUTPUT_ASSEMBLY.md
  - openspec/changes/impl-20260416-mm-rust-cutover-wave3-l3-assembly-rust-runtime/*
  - notes/sessions/2026-04-16/impl-mm-rust-cutover-wave3-l3-assembly-runtime/{project_state.md,open_tasks.md,handoff.md,meta.yaml}
- Behavior:
  - full payload 现在稳定输出 `agent_g.data.mm_flow`（优先显式字段，否则回填 `fused_signal.mm_flow`）。
  - delta payload 在 `changes.agent_g_data` 中显式输出 `mm_flow` 变化。
- Verification:
  - 新增 L3 payload/delta 合同测试通过。
  - strict validation 通过。

## Risks / Constraints
- Risk 1: L4 尚未基于 `agent_g.data.mm_flow` 做专门可视化映射，当前可通过原始 payload 消费。
- Risk 2: 工作区仍有大量历史未提交改动，本次未触碰其语义。

## Next Action
- Immediate Next Step: 进入后续 UI 会话，将 `mm_flow` 引入 L4 model/selector 并加回归测试。
- Owner: Codex

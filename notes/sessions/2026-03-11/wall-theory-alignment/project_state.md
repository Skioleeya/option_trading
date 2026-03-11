# Project State

## Snapshot
- DateTime (ET): 2026-03-11 10:42:25 -04:00
- Branch: master
- Last Commit: fc174d4
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 墙体分析理论对齐（RETREAT 语义统一 + 条件化 COLLAPSE + wall_context 透传）。
- Scope In:
  - L1 产出 `wall_context`（`gamma_regime/hedge_flow_intensity/counterfactual_vol_impact_bps`）
  - L3 Wall Dyn 分类由单标签升级为几何态+风险态（保持兼容）
  - L1→L3 合同透传与回归测试、SOP 同步
- Scope Out:
  - 不改 Rust 组件
  - 不变更外部 API 路由
  - 不调整非墙体策略护栏

## What Changed (Latest Session)
- Files:
  - shared/models/microstructure.py
  - shared/config/market_structure.py
  - l1_compute/output/enriched_snapshot.py
  - l1_compute/reactor.py
  - l2_decision/agents/agent_b.py
  - l3_assembly/assembly/ui_state_tracker.py
  - l3_assembly/assembly/payload_assembler.py
  - l3_assembly/presenters/ui/micro_stats/{thresholds.py,wall_dynamics.py,presenter.py,mappings.py}
  - l3_assembly/tests/{test_micro_stats_wall_dynamics.py,test_ui_state_tracker.py,test_assembly.py}
  - l1_compute/tests/test_reactor.py
  - docs/SOP/{L1_LOCAL_COMPUTATION.md,L3_OUTPUT_ASSEMBLY.md}
- Behavior:
  - `RETREATING_SUPPORT` 默认归入 `RETREAT`（几何态语义统一）。
  - `COLLAPSE` 改为条件触发：仅 `put retreat + SHORT_GAMMA + high hedge_flow_intensity`。
  - L1 新增 `wall_context` 并写入 `microstructure.wall_context` 与 `wall_migration.wall_context`。
  - L3 透传 `wall_context`，MicroStats 分类使用上下文门控。
- Verification:
  - 定向回归：70 passed（L1/L3 wall 相关）
  - L3 全量：129 passed
  - L2 关键子集：83 passed

## Risks / Constraints
- Risk 1: `l2_decision/tests/test_reactor_and_guards.py` 在当前环境因临时目录权限失败（与本改动无关）。
- Risk 2: `hedge_flow_intensity` 使用近墙体量代理，后续可接入更高精度盘口流动性指标。

## Next Action
- Immediate Next Step: 进入上线前观测阶段，校准 `wall_collapse_flow_intensity_threshold`。
- Owner: Codex

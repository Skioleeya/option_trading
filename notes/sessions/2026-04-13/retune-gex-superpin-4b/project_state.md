# Project State

## Snapshot
- DateTime (ET): 2026-04-13 15:55:26 -04:00
- Branch: chore/sync-all-local-changes-20260313
- Last Commit: 00a88fd
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 将 GEX 分级阈值重标定到 0.8B/4B，使 4B+ 显示 SUPER PIN。
- Scope In:
  - `gex_neutral_threshold` / `gex_super_pin_threshold` 配置下调
  - L1 分类边界测试补齐
  - SOP 同步与在线链路验收
- Scope Out:
  - 不改负 GEX 语义（仍为 ACCELERATION）
  - 不改 L3/L4 状态映射文案

## What Changed (Latest Session)
- Files:
  - shared/config/agent_g.py
  - l1_compute/tests/test_gex_classifier_thresholds.py
  - docs/SOP/L1_LOCAL_COMPUTATION.md
- Behavior:
  - GEX 正向分级阈值更新为：`<800 => NEUTRAL`、`[800,4000) => DAMPING`、`>=4000 => SUPER_PIN`（MMUSD）
  - 负 GEX 保持 `ACCELERATION`
- Verification:
  - `scripts/test/run_pytest.ps1 l1_compute/tests/test_gex_classifier_thresholds.py app/tests/test_ui_state_tracker_gex_regime.py app/tests/test_micro_stats_net_gex_contract.py` -> 11 passed
  - 提权重启后端后，在线 `history` 最新 12 条均为 `net_gex > 4000` 且 `gex_regime=SUPER_PIN`、`micro_stats.net_gex.label=SUPER PIN`

## Risks / Constraints
- Risk 1: 历史接口回看可能混有重启前样本，验收需看“最新窗口”。
- Risk 2: 该阈值调整会提升 SUPER PIN 触发频率，需盘中持续观察策略敏感度。

## Next Action
- Immediate Next Step: 运行 strict 校验并完成 handoff 归档。
- Owner: Codex

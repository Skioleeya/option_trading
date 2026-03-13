# Project State

## Snapshot
- DateTime (ET): 2026-03-12 11:29:29 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 按机构口径实现 GEX/Wall/Flip 语义修正，并保持跨层兼容。
- Scope In:
  - L1 GEX 主公式切换到 1% 现货变动口径（`*0.01`）。
  - StreamingAggregator 增加 `zero_gamma_level`，拆分 `flip_level_cumulative`。
  - Wall 规则改为 spot 同侧优先 + 全局回退。
  - L2 `gamma_flip` 改为 `spot vs zero_gamma_level` 判定。
  - L3 `gamma_flip_level` 绑定 `zero_gamma_level`，DepthProfile 继续使用 cumulative flip。
  - 对应单元测试与 SOP 同步。
- Scope Out:
  - L0 ingest / Rust runtime 逻辑。
  - UI 组件视觉改造（仅契约字段对齐）。

## What Changed (Latest Session)
- Files:
  - `l1_compute/compute/gpu_greeks_kernel.py`
  - `l1_compute/analysis/bsm_fast.py`
  - `l1_compute/compute/compute_router.py`
  - `l1_compute/aggregation/streaming_aggregator.py`
  - `l1_compute/reactor.py`
  - `l1_compute/output/enriched_snapshot.py`
  - `l2_decision/agents/services/gamma_qual_analyzer.py`
  - `l2_decision/agents/services/greeks_extractor.py`
  - `l3_assembly/assembly/payload_assembler.py`
  - `l1_compute/tests/test_compute.py`
  - `l1_compute/tests/test_streaming_aggregator.py`
  - `l1_compute/tests/test_reactor.py`
  - `l2_decision/tests/test_gamma_qual_analyzer.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
- Behavior:
  - `gex_per_contract` 改为 `gamma*OI*mult*S^2*0.01/1e6`（MMUSD）。
  - `total_call_gex/total_put_gex` 维持非负幅度，`net_gex=call-put` 不变。
  - 增加 `zero_gamma_level`（spot 网格重算过零），并显式保留 `flip_level_cumulative`。
  - `call_wall/put_wall` 采用 spot 同侧优先，缺失时回退全局最大。
  - `gamma_flip` 从 `net_gex<0` 切换为优先 `spot < zero_gamma_level`。
  - 对外 `gamma_flip_level` 指向 `zero_gamma_level`；DepthProfile 使用 cumulative flip。
- Verification:
  - `scripts/test/run_pytest.ps1 l2_decision/tests/test_gamma_qual_analyzer.py l1_compute/tests/test_streaming_aggregator.py l1_compute/tests/test_compute.py` -> `30 passed`
  - `scripts/test/run_pytest.ps1 l1_compute/tests/test_compute.py l1_compute/tests/test_streaming_aggregator.py l1_compute/tests/test_reactor.py l2_decision/tests/test_gamma_qual_analyzer.py l3_assembly/tests/test_assembly.py` -> `80 passed`

## Risks / Constraints
- Risk 1: `zero_gamma_level` 为离散网格估算值（161 点），极端 IV 形态下对插值精度敏感。
- Risk 2: `gamma_flip_level` 语义切换后，历史比较看板可能出现阈值行为变化。

## Next Action
- Immediate Next Step: 盘中跟踪 `zero_gamma_level` 与 `gamma_flip` 告警触发稳定性。
- Owner: Codex

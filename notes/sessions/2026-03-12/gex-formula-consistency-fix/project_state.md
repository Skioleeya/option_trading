# Project State

## Snapshot
- DateTime (ET): 2026-03-12 10:01:14 -04:00
- Branch: `master`
- Last Commit: `352c306b7d8f58629220416086ac2d2647e77894`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED` (offline test-only validation in this session)
  - L0-L4 Pipeline: `OK` (code-level)

## Current Focus
- Primary Goal: 修复 GEX/Call Wall/Put Wall 公式一致性与 wall_context 量纲错误。
- Scope In: `l1_compute/analysis/bsm_fast.py`、`l1_compute/reactor.py`、L1 相关测试与 SOP。
- Scope Out: 策略阈值、前端字段与接口扩展。

## What Changed (Latest Session)
- Files:
  - `l1_compute/analysis/bsm_fast.py`
  - `l1_compute/compute/compute_router.py`
  - `l1_compute/reactor.py`
  - `l1_compute/tests/test_compute.py`
  - `l1_compute/tests/test_reactor.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
- Behavior:
  - legacy 聚合 GEX 公式与主链路统一为 `gamma * OI * multiplier * S^2 / 1e6`（去除 `*0.01` 口径分叉）。
  - `near_wall_hedge_notional_m` 修正为百万美元单位直传，不再额外 `/1_000_000`。
  - L1 日志补充 GEX 口径标识（MMUSD + 公式）。
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_compute.py l1_compute/tests/test_reactor.py l1_compute/tests/test_streaming_aggregator.py` 通过（40 passed）。

## Risks / Constraints
- Risk 1: 工作区存在并行未提交变更，本次仅在目标文件内增量修改。
- Risk 2: `bsm_fast` 仍保留 legacy `total_put_gex` 符号约定（负值），本次未改该契约。

## Next Action
- Immediate Next Step: 执行并通过 `scripts/validate_session.ps1 -Strict`，完成会话门禁。
- Owner: Codex

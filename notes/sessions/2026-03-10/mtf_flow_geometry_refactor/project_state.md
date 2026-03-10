# Project State

## Snapshot
- DateTime (ET): 2026-03-10 14:37:00 -04:00
- Branch: master
- Last Commit: 368c9b9
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 实装独立 `tools/momentum_calibration` 工具链，用 Longbridge 1m K线完成 MOMENTUM 阈值首轮校准，并预留 Research 接口。
- Scope In:
  - 根目录新增模块化目录 `tools/momentum_calibration/`（sources/features/optimize/eval/io/workflows/tests）。
  - Stage1/Stage2/Stage3 三个 CLI 入口可独立运行并写出产物。
  - 固定 `bbo_confirmation_min=0.1`、`max_roc_reference`、`confidence_floor`，仅优化 ROC 双阈值。
  - 预留 `ResearchFeatureProvider.load(...)` 接口，当前返回 `None` 降级运行。
- Scope Out:
  - 不自动回写线上 `l2_decision/config/signals/momentum_signal.yaml`。
  - 不改 L0-L4 实时链路逻辑。

## What Changed (Latest Session)
- Files:
  - tools/momentum_calibration/config.py
  - tools/momentum_calibration/models.py
  - tools/momentum_calibration/sources/longbridge_kline.py
  - tools/momentum_calibration/sources/research_adapter.py
  - tools/momentum_calibration/features/kline_features.py
  - tools/momentum_calibration/optimize/roc_threshold_search.py
  - tools/momentum_calibration/eval/oos_eval.py
  - tools/momentum_calibration/io/report_writer.py
  - tools/momentum_calibration/workflows/stage1_train.py
  - tools/momentum_calibration/workflows/stage2_oos.py
  - tools/momentum_calibration/workflows/stage3_weekly_roll.py
  - tools/momentum_calibration/tests/*
  - tools/momentum_calibration/README.md
  - docs/SOP/L2_DECISION_ANALYSIS.md
- Behavior:
  - 新增离线校准工具链，完全独立于 L0-L4 运行时导入路径。
  - `LongbridgeKlineSource` 实装 ET 标准化、`max_rps=3/max_concurrency=2` 预算、官方上限硬保护与指数退避。
  - Stage1 输出 `candidate_momentum_signal.yaml + metrics_train.json`。
  - Stage2 按“前一月”窗口输出 `metrics_oos.json`（写回 stage1 产物目录）。
  - Stage3 按周滚动输出 `weekly_roll.csv` 与 `metrics_roll.json`（默认 22 交易日窗）。
  - Research 特征接口已落位但默认不可用，不阻塞主流程。
- Verification:
  - `python -m py_compile tools/momentum_calibration/...` 通过。
  - `scripts/test/run_pytest.ps1 tools/momentum_calibration/tests`：9 passed。
  - `stage1_train.py` 实跑通过，生成 run_id `stage1_SPY_US_20260310_143505`。
  - `stage2_oos.py` 实跑通过，OOS 指标写入同 run 目录。
  - `stage3_weekly_roll.py --weeks 4` 实跑通过，生成 `stage3_SPY_US_20260310_143659/weekly_roll.csv`。

## Risks / Constraints
- Risk 1: 单纯 K线校准会弱化微观结构信息，阈值泛化能力受限（已通过 research adapter 预留后续扩展位）。
- Risk 2: 仓内既有 `debugHotkey.integration.test.tsx` TS 错误仍阻断 `npm build` 全绿（与本次工具链无关）。

## Next Action
- Immediate Next Step: 用 stage3 每周任务持续产出滚动阈值轨迹，待 research 历史充足后接入 ResearchFeatureProvider 联合优化 BBO 门限。
- Owner: Codex

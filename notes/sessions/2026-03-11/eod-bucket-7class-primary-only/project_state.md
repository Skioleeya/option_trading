# Project State

## Snapshot
- DateTime (ET): 2026-03-11 17:15:00 -04:00
- Branch: `master`
- Last Commit: `fecc2ae`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DOWN` (backend stopped by user)
  - L0-L4 Pipeline: `DOWN`

## Current Focus
- Primary Goal: EOD 分类从 3 类扩到 7 类，并切换为主标签唯一输出。
- Scope In:
  - `eod_bucket_thresholds.json` 升级为分组阈值 + 优先级
  - `eod_bucket_archive.py` 增加 7 类判定与主标签选择
  - `test_eod_bucket_archive.py` 覆盖逐类命中、冲突优先级与降级场景
- Scope Out:
  - 不改 L0-L4 实时运行逻辑
  - 不引入外部事件日历

## What Changed (Latest Session)
- Files:
  - `scripts/diagnostics/config/eod_bucket_thresholds.json`
  - `scripts/diagnostics/eod_bucket_archive.py`
  - `scripts/test/test_eod_bucket_archive.py`
  - `scripts/README.md`
- Behavior:
  - 新增类别：`gap_trend_day / vol_crush_day / pinning_day / whipsaw_day`
  - 输出切换为 `primary_tag` 单一分桶，保留 `matched_tags` 审计信息
  - manifest 中 `tags` 固定为 `[primary_tag]`
- Verification:
  - 脚本测试 `12 passed`
  - 实盘 dry-run（20260311）两次输出一致：`primary=range_day`
  - `daily` 与 `by_regime/<primary>` manifest `source_files` 一致

## Risks / Constraints
- Risk 1: 当前阈值为固定 V1，仍需连续交易日校准。
- Risk 2: `gap_trend_day` 依赖前一交易日 raw 文件，缺失时自动降级不命中。

## Next Action
- Immediate Next Step: 观测 3-5 个交易日主标签分布，按误判样本调参。
- Owner: Quant Research

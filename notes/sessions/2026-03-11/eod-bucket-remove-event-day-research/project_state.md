# Project State

## Snapshot
- DateTime (ET): 2026-03-11 17:02:00 -04:00
- Branch: `master`
- Last Commit: `fecc2ae`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DOWN` (backend stopped by user)
  - L0-L4 Pipeline: `DOWN`

## Current Focus
- Primary Goal: 取消 `event_day` 分类并给出 2024-2026 论文驱动的交易日分类前沿分析。
- Scope In:
  - 移除 `event_day` 标签判定与阈值
  - 更新脚本说明与单测
  - 整理 Google Scholar 方向文献结论
- Scope Out:
  - 不改动 L0-L4 运行时链路
  - 不引入外部事件日历到生产逻辑

## What Changed (Latest Session)
- Files:
  - `scripts/diagnostics/eod_bucket_archive.py`
  - `scripts/diagnostics/config/eod_bucket_thresholds.json`
  - `scripts/test/test_eod_bucket_archive.py`
  - `scripts/README.md`
- Behavior:
  - EOD 分桶仅保留 `trend_day/range_day/high_vol_open`
  - `event_day` 不再参与标签判定
  - 保留 `max_abs_jump` 作为诊断指标，不参与打标
- Verification:
  - 新增测试全通过
  - 20260311 dry-run 输出只含非 `event_day` 标签

## Risks / Constraints
- Risk 1: 取消 `event_day` 后，突发跳变日只能通过其他标签间接表达。
- Risk 2: 论文调研结论为方法映射，不等同于直接可交易参数。

## Next Action
- Immediate Next Step: 基于文献方法补一版“细分交易日 taxonomy + 阈值校准实验计划”。
- Owner: Quant Research

# Project State

## Snapshot
- DateTime (ET): 2026-03-11 16:40:00 -04:00
- Branch: `master`
- Last Commit: `fecc2ae`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DOWN` (backend stopped by user)
  - L0-L4 Pipeline: `DOWN` (expected with backend stopped)

## Current Focus
- Primary Goal: 实现 EOD 自动分桶（规则阈值 + Manifest 索引 + 调度命令）并可回归验证。
- Scope In:
  - `scripts/diagnostics/eod_bucket_archive.py`
  - `scripts/diagnostics/config/eod_bucket_thresholds.json`
  - `scripts/ops/register_eod_bucket_task.ps1`
  - `scripts/test/test_eod_bucket_archive.py`
  - `scripts/README.md`
- Scope Out:
  - 不改动 L0-L4 运行时业务链路
  - 不引入外部事件日历
  - 不做原始文件复制归档

## What Changed (Latest Session)
- Files:
  - 新增 EOD 分桶脚本、阈值配置、任务注册脚本、pytest
  - 更新 scripts 文档入口
- Behavior:
  - 每日读取 `data/research/raw|feature|label` 与 `atm|mtf|wall` 冷存文件
  - 输出 `data/cold/daily/<date>/manifest.json`
  - 输出 `data/cold/by_regime/<tag>/<date>/manifest.json`（索引式，不复制原始文件）
  - 输出 `data/cold/reports/<date>_quality.json`
  - `--strict-quality` 低质量日返回码 `2`
- Verification:
  - `scripts/test/test_eod_bucket_archive.py` 全通过
  - 20260311 实盘 dry-run 两次，结果幂等，`daily` 与 `by_regime` source 索引一致

## Risks / Constraints
- Risk 1: 当日分类依赖 `raw` 指标字段，若缺列将降级为 `LOW_QUALITY_DAY`。
- Risk 2: 调度任务默认依赖本机时区与 `python` 路径，需要在目标机器确认。

## Next Action
- Immediate Next Step: 将计划任务注册到目标机器并连续观察 3 个交易日分桶质量报告。
- Owner: Quant Ops

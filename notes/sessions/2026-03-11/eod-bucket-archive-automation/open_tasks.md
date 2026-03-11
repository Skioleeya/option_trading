# Open Tasks

## Priority Queue
- [x] P0: EOD 自动分桶脚本与阈值配置落库
  - Owner: Codex
  - Definition of Done: CLI 可执行、输出 daily/by_regime manifest + quality report、严格质量门禁返回码生效
  - Blocking: None
- [x] P1: 调度注册脚本落库（16:10 主任务 + 17:00 重试）
  - Owner: Codex
  - Definition of Done: 产出可直接执行的 `schtasks /Create` 命令并支持 `-Apply`
  - Blocking: None
- [x] P1: 分桶脚本测试覆盖
  - Owner: Codex
  - Definition of Done: 单测覆盖多标签/阈值边界/低质量返回码
  - Blocking: None
- [ ] P2: 连续 3 个交易日观察质量报告与标签稳定性
  - Owner: Quant Ops
  - Definition of Done: `reports/YYYYMMDD_quality.json` 无异常漂移并形成阈值微调建议
  - Blocking: 需要后端连续运行

## Parking Lot
- [ ] 外部事件日历接入（FOMC/CPI/财报）作为 `event_day` 补充判定
- [ ] 结果汇总看板（按 regime 的样本覆盖和质量趋势）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] EOD 自动分桶实现与验证完成（2026-03-11 16:40 ET）

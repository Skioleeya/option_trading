# Open Tasks

## Priority Queue
- [x] P0: 取消 `event_day` 判定
  - Owner: Codex
  - Definition of Done: 分类函数不再生成 `event_day`，配置移除对应阈值，测试通过
  - Blocking: None
- [x] P1: 同步更新 EOD 脚本说明与验证
  - Owner: Codex
  - Definition of Done: README 描述与 dry-run 结果一致
  - Blocking: None
- [ ] P2: 按论文方法扩展细分交易日 taxonomy
  - Owner: Quant Research
  - Definition of Done: 输出可执行的类别定义与校准方案（含回测分层）
  - Blocking: 需补充更长样本

## Parking Lot
- [ ] 外部事件日历接入（未来若恢复事件类标签）
- [ ] 类别置信度评分与冲突消解策略

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] event_day 分类移除 + 单测/干跑验证（2026-03-11 17:02 ET）

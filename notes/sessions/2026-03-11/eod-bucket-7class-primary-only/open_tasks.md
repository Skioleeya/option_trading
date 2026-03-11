# Open Tasks

## Priority Queue
- [x] P0: 完成 7 类主标签规则与阈值配置
  - Owner: Codex
  - Definition of Done: 配置与分类器均支持 7 类 + 主标签优先级
  - Blocking: None
- [x] P1: 完成测试扩展与冲突优先级验证
  - Owner: Codex
  - Definition of Done: 覆盖逐类命中/冲突/降级/质量门禁/幂等
  - Blocking: None
- [ ] P2: 连续交易日阈值校准
  - Owner: Quant Research
  - Definition of Done: 输出误判样本复盘与阈值调整建议
  - Blocking: 需要更多真实交易日样本

## Parking Lot
- [ ] 引入类别置信度分数（非二元命中）
- [ ] 引入事件日历后再评估是否恢复事件标签

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 3 类扩到 7 类（主标签唯一）并完成验证（2026-03-11 17:15 ET）

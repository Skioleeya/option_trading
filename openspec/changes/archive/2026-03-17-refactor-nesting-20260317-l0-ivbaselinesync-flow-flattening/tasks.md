# Tasks

## Scope
- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）

## Implementation
- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）

## Verification
- [x] 相关测试通过（scripts/test/run_pytest.ps1）
- [x] 指标达标（见量化门槛）
- [x] SOP 同步或写明 SOP-EXEMPT

## DoD
- [x] 复杂度/嵌套/长度/重复率达到阈值
- [x] 无行为回归
- [x] 变更可回滚、可审计

## Phase 1 - Baseline & Flow Freeze
- [x] 冻结 warm_up/_staggered_sync baseline
- [x] 冻结 dedupe/cooldown/chunk 语义
- [x] 冻结非目标范围

## Phase 2 - Scheduler Skeleton Split
- [x] 提取批次遍历骨架
- [x] 提取 chunk 遍历骨架
- [x] 保持原有日志顺序

## Phase 3 - Parser Split
- [x] 提取 implied volatility 解析器
- [x] 提取 open interest 解析器
- [x] 去除 warm_up/staggered 重复解析

## Phase 4 - Cooldown Strategy Split
- [x] 提取 301607 识别与 cooldown 处理
- [x] 保留 warm_up/staggered 不同 sleep 策略
- [x] 统一错误日志结构

## Phase 5 - spot_at_sync Timing Split
- [x] 提取 spot_at_sync 写入 helper
- [x] 保留 warm_up 固定 spot 语义
- [x] 保留 staggered 按 batch spot 语义

## Phase 6 - Logging & Observability Cleanup
- [x] 统一批次日志模板
- [x] 统一周期起止日志模板
- [x] 保留关键兼容 marker

## Phase 7 - Regression & Equivalence
- [x] dedupe/chunk/cooldown 回归通过
- [x] spot_at_sync 语义回归通过
- [x] before/after 指标留痕

## Phase 8 - Gate Closure
- [x] quality gate 通过
- [x] strict gate 通过
- [x] session/context 文档同步

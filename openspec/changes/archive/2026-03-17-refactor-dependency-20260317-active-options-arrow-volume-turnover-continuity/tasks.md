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

## Phase 1 - Baseline Evidence
- [x] 记录 `min_volume` 触发日志基线
- [x] 记录 `chain_size/ws_volume_seen/ws_current_volume_seen/ws_turnover_seen` 基线
- [x] 记录 Arrow schema 当前字段清单

## Phase 2 - Contract Mapping Freeze
- [x] 冻结 `volume/current_volume/turnover` 语义表
- [x] 冻结字段缺失时的回退规则
- [x] 冻结非目标字段不改承诺

## Phase 3 - Arrow Contract Patch
- [x] 补齐 Arrow 合同字段映射
- [x] 保持既有字段兼容
- [x] 为字段新增最小测试覆盖

## Phase 4 - Housekeeping Continuity
- [x] 校准 housekeeping 对 Arrow 行数据的读取兼容
- [x] 校准 `current_volume -> volume` 回退路径
- [x] 校准异常数据下的保护逻辑

## Phase 5 - Runtime Filter Consistency
- [x] 对齐 runtime 过滤输入合同
- [x] 验证过滤前后数据统计可观测
- [x] 验证占位分支触发条件可解释

## Phase 6 - Regression and Quality Gate
- [x] 执行目标 pytest 集并留痕
- [x] 执行质量门禁并留痕
- [x] 执行边界扫描并留痕

## Phase 7 - Strict Gate
- [x] 执行 `scripts/validate_session.ps1 -Strict`
- [x] 写入 strict 证据到会话 handoff
- [x] 处理 strict 失败项直至通过

## Phase 8 - Closure
- [x] 汇总 before/after 量化结果
- [x] 汇总风险与回滚说明
- [x] 回填父提案进度与 DoD 状态

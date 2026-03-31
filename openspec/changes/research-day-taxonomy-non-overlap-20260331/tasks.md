# Tasks

## Phase 1 - Taxonomy Freeze
- [ ] 冻结 canonical 枚举并写入实现说明：`primary_day_type`、`context_modifiers`、`close_profile`。

## Phase 2 - Metric Contract
- [ ] 为 `trend_day`、`reversal_day`、`balance_day`、`whipsaw_day` 输出一张指标合同表，明确每个主标签依赖的路径指标与排除条件。
- [ ] 为每个 modifier 输出一张修饰符合同表，明确触发指标、是否可与其他 modifier 共存、以及不得改变主标签的约束。
- [ ] 产出一份边界样本清单，至少包含 1 个 `reversal_day` 与 1 个 `whipsaw_day` 对照样本。

## Phase 3 - Output Schema
- [ ] 为 cold manifest / quality report / classifier return payload 产出统一字段清单，字段名必须逐字一致。
- [ ] 明确 hard-cut 后必须移除的 legacy 字段清单：`primary_tag`、`legacy_primary_tag`、`matched_tags`。

## Phase 4 - Research Validation
- [ ] 用固定样本集回放验证新 taxonomy，输出一份样本日判定表。
- [ ] 固定样本集至少包含：1 个 `trend_day`、1 个 `trend_day + gap_open`、1 个 `balance_day + pinning`、1 个 `whipsaw_day`、1 个 `reversal_day`。
- [ ] 将 2026-03-30 纳入固定样本集，并记录其 canonical 判定结果。

## Phase 5 - Implementation
- [ ] 更新 `scripts/diagnostics/eod_bucket_metrics.py`
- [ ] 更新 `scripts/diagnostics/eod_bucket_rules.py`
- [ ] 更新 `scripts/diagnostics/eod_bucket_archive.py`
- [ ] 清理 active cold archive 中无法继续保留的 legacy-only manifest / by_regime 索引。
- [ ] 更新相关 SOP 与研究文档，确保 canonical 字段和样本验证口径一致。

## Phase 6 - Verification
- [ ] 补充分类器单测，覆盖主标签互斥性、modifier 正交性和 hard-cut 后 legacy 字段缺失断言。
- [ ] 执行样本回归，确认固定样本集判定不漂移。
- [ ] 执行 `scripts/validate_session.ps1 -Strict`。
- [ ] 同步 session/context/handoff 证据。

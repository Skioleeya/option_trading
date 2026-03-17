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

## Phase 1 - Baseline & Hotspot Freeze
- [x] 冻结 AgentG baseline 指标
- [x] 冻结输出合同字段
- [x] 冻结非目标范围

## Phase 2 - Input Adaptation Split
- [x] 抽离输入读取与默认值逻辑
- [x] 抽离 snapshot/object parity 访问器
- [x] 保持调用方签名不变

## Phase 3 - Microstructure Aggregation Split
- [x] 抽离 per_strike 聚合器
- [x] 抽离 micro_flow 信号构建
- [x] 抽离 avg_atm_vpin 诊断逻辑

## Phase 4 - Risk Gate Split
- [x] 抽离 jump gate 早返回构建
- [x] 抽离 dealer squeeze 标记抽取
- [x] 抽离 VRP veto 状态处理

## Phase 5 - Fusion Decision Split
- [x] 抽离 fused signal payload 组装
- [x] 抽离 confidence 调整链
- [x] 抽离 final signal 路由逻辑

## Phase 6 - Result Builder Split
- [x] 抽离 AgentResult 数据组装器
- [x] 统一 summary 拼接策略
- [x] 保持日志语义不变

## Phase 7 - Regression & Equivalence
- [x] 关键决策分支回归测试通过
- [x] 无合同字段漂移
- [x] 指标 before/after 完整留痕

## Phase 8 - Gate Closure
- [x] quality gate 通过
- [x] strict gate 通过
- [x] session/context 文档同步

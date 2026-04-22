# Tasks

## Scope
- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）

## Implementation
- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）

## Verification
- [ ] 相关测试通过（scripts/test/run_pytest.ps1）
- [x] 指标达标（见量化门槛）
- [x] SOP 同步或写明 SOP-EXEMPT

## DoD
- [x] 复杂度/嵌套/长度/重复率达到阈值
- [ ] 无行为回归
- [x] 变更可回滚、可审计

## Phase 1 - Extractor Domain Inventory
- [x] 盘点 extractor 分类与依赖关系（flow/skew/vol/common）
- [x] 标记 stateful 与 stateless 提取器边界
- [x] 冻结 feature name 与语义合同

## Phase 2 - Module Partition Plan
- [x] 设计目标模块切分与文件命名
- [x] 设计共享 helper 的归属与依赖方向
- [x] 设计 registry 聚合入口

## Phase 3 - Common Helper Extraction
- [x] 抽离 `_get_val/_get_agg/_safe` 等公共函数
- [x] 抽离记录批处理通用工具
- [x] 抽离版本/缓存 key 规范化工具

## Phase 4 - Theme Module Extraction
- [x] 抽离 flow 主题提取器
- [x] 抽离 skew 主题提取器
- [x] 抽离 volatility 主题提取器

## Phase 5 - Registry Stabilization
- [x] 重建 `build_default_extractors` 聚合逻辑
- [x] 校验 feature 注册顺序与名称不变
- [x] 校验 stateful extractor reset 入口不变

## Phase 6 - Quant Gate
- [x] 校验拆分后各文件 LOC <= 450
- [x] 校验关键函数复杂度/嵌套达标
- [x] 形成 before/after 指标对照

## Phase 7 - Regression Gate
- [ ] 执行 feature store 与 institutional logic 相关 pytest
- [x] 覆盖 RecordBatch 与 fallback 路径
- [ ] 校验无行为语义回归

## Phase 8 - Close-out
- [x] 执行 strict validate 并记录结果
- [x] 更新 handoff 的风险与回滚说明
- [x] 输出可归档证据包

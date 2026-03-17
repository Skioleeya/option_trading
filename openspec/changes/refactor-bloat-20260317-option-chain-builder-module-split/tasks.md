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

## Phase 1 - File Bloat Baseline
- [x] 记录 `option_chain_builder.py` 当前 LOC、函数长度、类长度
- [x] 识别超过阈值的函数与职责块
- [x] 冻结 before 指标用于对比

## Phase 2 - Split Blueprint
- [x] 制定目标模块清单与命名规范
- [x] 制定公共接口与导入路径
- [x] 制定拆分顺序（先 helper 后主流程）

## Phase 3 - Helper Extraction
- [x] 抽离 payload 标准化 helper
- [x] 抽离 Rust 事件桥接 helper
- [x] 抽离 callback dispatch helper

## Phase 4 - Orchestration Slimming
- [x] 收缩 `OptionChainBuilder` 仅保留编排职责
- [x] 删除重复逻辑并统一入口
- [x] 确认主循环异常处理语义不变

## Phase 5 - Import & Boundary Cleanup
- [x] 校验拆分后 import 方向无退化
- [x] 校验无跨层私有成员访问
- [x] 校验无 wildcard import

## Phase 6 - Quant Gate
- [x] 校验拆分后各文件 LOC <= 450
- [x] 校验关键函数复杂度/嵌套达标
- [x] 输出 before/after 指标表

## Phase 7 - Regression Gate
- [ ] 运行 builder 相关 pytest 集
- [x] 运行桥接路径 smoke 校验
- [ ] 记录回归结果与性能影响

## Phase 8 - Close-out
- [x] 运行 strict gate 并留痕
- [x] 更新 handoff 与风险回滚说明
- [x] 形成可归档证据清单

# Tasks

## Scope
- [ ] 锁定目标文件清单（Top N）
- [ ] 标记非目标范围（避免扩散）

## Implementation
- [ ] 重构实现（仅本主题）
- [ ] 边界扫描（无跨层违规 import）
- [ ] 魔法数治理（若本主题涉及）

## Verification
- [ ] 相关测试通过（scripts/test/run_pytest.ps1）
- [ ] 指标达标（见量化门槛）
- [ ] SOP 同步或写明 SOP-EXEMPT

## DoD
- [ ] 复杂度/嵌套/长度/重复率达到阈值
- [ ] 无行为回归
- [ ] 变更可回滚、可审计

## Phase 1 - File Bloat Baseline
- [ ] 记录 `option_chain_builder.py` 当前 LOC、函数长度、类长度
- [ ] 识别超过阈值的函数与职责块
- [ ] 冻结 before 指标用于对比

## Phase 2 - Split Blueprint
- [ ] 制定目标模块清单与命名规范
- [ ] 制定公共接口与导入路径
- [ ] 制定拆分顺序（先 helper 后主流程）

## Phase 3 - Helper Extraction
- [ ] 抽离 payload 标准化 helper
- [ ] 抽离 Rust 事件桥接 helper
- [ ] 抽离 callback dispatch helper

## Phase 4 - Orchestration Slimming
- [ ] 收缩 `OptionChainBuilder` 仅保留编排职责
- [ ] 删除重复逻辑并统一入口
- [ ] 确认主循环异常处理语义不变

## Phase 5 - Import & Boundary Cleanup
- [ ] 校验拆分后 import 方向无退化
- [ ] 校验无跨层私有成员访问
- [ ] 校验无 wildcard import

## Phase 6 - Quant Gate
- [ ] 校验拆分后各文件 LOC <= 450
- [ ] 校验关键函数复杂度/嵌套达标
- [ ] 输出 before/after 指标表

## Phase 7 - Regression Gate
- [ ] 运行 builder 相关 pytest 集
- [ ] 运行桥接路径 smoke 校验
- [ ] 记录回归结果与性能影响

## Phase 8 - Close-out
- [ ] 运行 strict gate 并留痕
- [ ] 更新 handoff 与风险回滚说明
- [ ] 形成可归档证据清单

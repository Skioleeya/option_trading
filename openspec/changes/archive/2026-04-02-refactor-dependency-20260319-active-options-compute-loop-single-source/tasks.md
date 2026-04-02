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

## Phase 1 - Baseline and Contract Freeze
- [x] 记录当前 ActiveOptions 输入路径与失败样本
- [x] 冻结单源输入字段合同草案
- [x] 冻结非目标算法范围

## Phase 2 - Shared State Contract
- [x] 新增 `ActiveOptionsInputSnapshot` 结构
- [x] 新增共享状态写入/读取接口
- [x] 添加字段默认值与原因码常量

## Phase 3 - ComputeLoop Producer Cut
- [x] 在 ComputeLoop 构建输入快照
- [x] 在 tick 流程发布到 SharedLoopState
- [x] 增加版本/时间戳一致性保护

## Phase 4 - Housekeeping Consumer Cut
- [x] Housekeeping 切换为只读共享快照
- [x] 移除跨层回补抓取分支
- [x] 无效输入时进入显式降级分支

## Phase 5 - Diagnostics Surface
- [x] `/debug/persistence_status` 增加输入通道诊断字段
- [x] 对齐字段命名与类型稳定性
- [x] 增加诊断字段单测断言

## Phase 6 - Unit and Integration Gate
- [x] 执行 loops 相关单测
- [x] 执行 active_options 相关单测
- [ ] 执行 `verify_active_options_hotfix.ps1`

## Phase 7 - Strict and Policy Gate
- [ ] 执行 `scripts/validate_session.ps1 -Strict`
- [ ] 核验 quality gate 与 openspec chain gate
- [ ] 记录失败项与修复闭环

## Phase 8 - Handoff and Closure
- [ ] 汇总输入链路变更与回滚策略
- [ ] 回填 session/context/handoff 证据
- [ ] 更新父提案进度并标记收口状态

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

## Phase 1 - Replay Source Contract
- [x] 定义 replay source date 选择规则
- [x] 定义非平台化窗口筛选规则
- [x] 定义时间重映射到 today ET 的规则

## Phase 2 - Tracker Integration
- [x] 新增 test-only replay service
- [x] Tracker 通过公共路径准备 today history/anchor
- [x] after-hours `update()` / `compute_current_decay()` 接入 replay

## Phase 3 - Validation Harness
- [x] 60s harness 增加历史动态性判定
- [x] 跑通 API/WS 浏览器级 replay 验证
- [x] 输出 tmp 工件并记录 session 证据

## Phase 4 - Governance and Handoff
- [ ] 执行 `scripts/validate_session.ps1 -Strict`
- [ ] 核验 quality gate 与 openspec chain gate
- [ ] 回填 session/context/handoff 证据

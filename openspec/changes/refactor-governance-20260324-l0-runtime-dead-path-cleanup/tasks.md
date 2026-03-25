# Tasks

## Governance
- [ ] 定义统一度量口径（复杂度/嵌套/重复率/魔法数）
- [ ] 定义子提案依赖图与执行顺序
- [ ] 定义回滚策略与风险分级

## Child Proposal Gate
- [ ] nesting 子提案创建并通过审查
- [ ] dependency 子提案创建并通过审查
- [ ] bloat 子提案创建并通过审查
- [ ] magic-number 子提案创建并通过审查

## Merge Gate
- [ ] 所有子提案 DoD 达成
- [ ] 量化 before/after 汇总完成
- [ ] Strict 校验通过并留痕

## Scope
- [x] 锁定 dead-path 清理范围
- [x] 冻结非目标边界（不改 L1/L2/L3 行为）

## Implementation
- [x] 清理孤立 runtime adapter
- [x] 清理重复事件处理器及其专属测试
- [x] 拆分超长 runtime 测试文件
- [x] 边界扫描（无新增跨层违规 import）

## Verification
- [ ] `scripts/test/run_pytest.ps1 l0_ingest/tests/v2`
- [ ] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Docs & Handoff
- [x] OpenSpec 记录落地
- [x] README / SOP 同步或在 handoff 写明 EXEMPT
- [ ] session/context/handoff 回填验证证据

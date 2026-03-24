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

## Phase 1 - Baseline Freeze
- [x] 固化本轮目标：`l0_ingest/v2` 成为唯一正式运行树
- [x] 固化本轮结构约束：禁止恢复 `l0_ingest/feeds/*` 平铺目录
- [x] 固化本轮边界：不改变 `fetch_snapshot()` 合同语义

## Phase 2 - Structure Refactor
- [x] 删除旧 `l0_ingest/feeds/*` 并将运行逻辑迁入分层 `v2` 子包
- [x] 删除顶层 `l0_ingest/subscription_manager.py`
- [x] 清退被跟踪的 `l0_ingest/l0_rust-0.1.0.dist-info/*`

## Phase 3 - Wiring
- [x] 修正 `l0_ingest/v2/*` 内部 import 到新层级
- [x] 通过轻量/惰性包出口切断 `v2` 循环导入
- [x] 修正 app 与测试引用到新路径

## Phase 4 - Docs & Governance
- [x] 更新 `l0_ingest/README.md`
- [x] 更新 `docs/SOP/L0_DATA_FEED.md`
- [x] 更新 `docs/SOP/SYSTEM_OVERVIEW.md`

## Phase 5 - Verification
- [x] `python -m compileall l0_ingest/v2 l0_ingest/tests/v2 app shared`
- [x] `scripts/test/run_pytest.ps1 l0_ingest/tests/v2 app/loops/tests/test_compute_loop_gpu_dedup.py app/loops/tests/test_housekeeping_gpu_dedup.py`
- [ ] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

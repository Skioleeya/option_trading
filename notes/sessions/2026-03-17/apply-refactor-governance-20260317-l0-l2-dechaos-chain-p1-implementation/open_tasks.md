# Open Tasks

## Priority Queue
- [x] P0: 建立父提案 + 两子提案 OpenSpec 治理链
  - Owner: Codex
  - Definition of Done: 三个 change-id 文档四件套齐全，tasks 含 8 phases，禁止项写入治理合同
  - Blocking: 无
- [x] P1: 完成 AgentG 去复杂化拆分并保持行为等价
  - Owner: Codex
  - Definition of Done: `_decide_impl` 明显降复杂度；相关回归测试通过；边界/质量/strict 门禁通过
  - Blocking: 无
- [x] P1: 完成 IVBaselineSync 流程扁平化并保持语义等价
  - Owner: Codex
  - Definition of Done: warm_up/staggered 拆分 helper；dedupe/cooldown/chunk 语义回归通过
  - Blocking: 无
- [x] P1: 完成本次父提案 /opsx-archive 归档
  - Owner: Codex
  - Definition of Done: 父+子提案目录迁入 `openspec/changes/archive/2026-03-17-*` 并 strict 复跑通过
  - Blocking: 无
- [x] P1: 更新 `启动步骤.md` 后端启动方法
  - Owner: Codex
  - Definition of Done: 明确后台/前台启动、degraded 回退、日志 tail 方法
  - Blocking: 无

## Parking Lot
- [ ] P2: 第二阶段硬阈值收口（将 AgentG 进一步打到质量阈值）
- [ ] P2: 补充 IVBaselineSync 端到端集成回归（包含真实 rate-limit 模拟）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] L0-L2 dechaos P1 implementation completed with strict pass (2026-03-17 18:37 ET)
- [x] `/opsx-archive` completed for current parent+children (2026-03-17 18:49 ET)
- [x] `启动步骤.md` backend startup method updated (2026-03-17 18:49 ET)

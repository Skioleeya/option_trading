## 1. Governance

- [x] 1.1 建立并链接子提案 A/B/C/D。
- [x] 1.2 固化子提案依赖顺序：`A -> B -> C -> D`，禁止越序合并。
- [x] 1.3 为每个子提案定义“文件范围 + 字段范围 + 测试范围”。

## 2. Boundary Gate

- [x] 2.1 要求所有 `GEX / wall / zero-gamma / FLOW / VRP / RR25` 语义改动都经由合同或中立说明模块，不在展示层私自修辞。
- [x] 2.2 要求字段改名采用兼容 alias 过渡，不允许一阶段内硬删除旧字段。
- [x] 2.3 要求每个子提案同步至少一个相关 SOP 文件。

## 3. Closure

- [x] 3.1 核验子提案状态：A/B/D 已实现完成；C unfinished residual 已在 reconciliation 中移交 follow-up `Phase E`。
- [x] 3.2 核验历史子提案测试入口与 strict 验证证据已在对应 session handoff/meta 存档。
- [x] 3.3 旧父提案归档为历史治理记录；residual closure 入口切换到 `formula-semantic-followup-parent-governance`。

## Reconciliation Evidence

- Phase A Evidence: `notes/sessions/2026-03-12/formula-semantic-phase-a-impl/`
- Phase B Evidence: `notes/sessions/2026-03-12/formula-semantic-phase-b-impl/`
- Phase D Evidence: `notes/sessions/2026-03-12/formula-semantic-phase-d-impl/`
- Phase C Handoff: `openspec/changes/formula-semantic-phase-c-provenance-and-heuristic-labels/tasks.md` -> follow-up `Phase E`

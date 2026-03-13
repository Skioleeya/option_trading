## 1. Governance

- [x] 1.1 建立并链接 child proposals `E/F/G/H`
- [x] 1.2 固化依赖顺序 `E -> F -> G -> H`
- [x] 1.3 在父提案中明确旧家族 A/B/D 为已实现历史、旧 C residual 交由新 E 接管

## 2. Boundary Gate

- [x] 2.1 要求 `VRP / GEX / wall / flip / FLOW / RR25 / charm` 的语义变更只能经由 shared/L1/L2 中立合同
- [x] 2.2 要求 live canonical cutover 只改 L3/L4 internal source-of-truth，不改顶层 wire shape
- [x] 2.3 要求每个 child 同步至少一个 SOP 或 operator-facing 文档（E/F/G 已同步 SOP；H 同步 old/new parent 与 child proposal/tasks reconciliation 文档）

## 3. Closure

- [x] 3.1 核验 `E/F/G/H` 全部完成
- [x] 3.2 核验旧/new proposals 不再同时声明同一 residual scope 为 active
- [x] 3.3 通过 strict validation 后完成父提案 closure

## Reconciliation Evidence

- `E`: `openspec/changes/formula-semantic-followup-phase-e-provenance-and-proxy-registry/tasks.md`
- `F`: `openspec/changes/formula-semantic-followup-phase-f-guard-unit-and-reference-sync/tasks.md`
- `G`: `openspec/changes/formula-semantic-followup-phase-g-live-canonical-contract-cutover/tasks.md`
- `H`: `openspec/changes/formula-semantic-followup-phase-h-openspec-reconciliation/tasks.md`

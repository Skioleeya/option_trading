# Open Tasks

## Priority Queue
- [x] P0: 完成仓库指标定位与本地公式审计
  - Owner: Codex
  - Definition of Done: 用户列出的 L1/L2/Shared 指标均能落到具体实现文件并给出公式/阈值/单位
  - Blocking: None
- [x] P0: 完成 2024-2026 论文检索与源手册
  - Owner: Codex
  - Definition of Done: 源手册覆盖 gamma/hedging、IV surface/skew、VRP、option flow/OI 相关论文
  - Blocking: None
- [x] P1: 完成 session/context 同步并通过 strict gate
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passed
  - Blocking: None

## Parking Lot
- [ ] 如后续数据源新增 dealer/customer/open-close 标签，补一版 inventory-truth 与 OI-proxy 的双口径审计
- [ ] 若用户后续要求修复口径，可据本报告单独开 session 做 runtime/doc 修正

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 新建 session `2026-03-12/option-paper-formula-audit-2024-2026`（2026-03-12 12:28 ET）
- [x] 完成本地实现扫描与公式定位（2026-03-12 12:39 ET）
- [x] 完成 2024-2026 论文检索与两份 `docs/` 报告（2026-03-12 12:45 ET）
- [x] `scripts/validate_session.ps1 -Strict` 通过（2026-03-12 12:48 ET）

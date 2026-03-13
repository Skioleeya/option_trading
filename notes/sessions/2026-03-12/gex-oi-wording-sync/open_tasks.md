# Open Tasks

## Priority Queue
- [x] P0: 将当前生效 GEX 语义文案统一为 `OI-based proxy`
  - Owner: Codex
  - Definition of Done: 当前 SOP、代码注释和 session/context 文案不再把现有 Longbridge 驱动的 GEX 表述为 dealer inventory 真值
  - Blocking: None
- [x] P1: 标注 `example.py` 为外部库存重建示例
  - Owner: Codex
  - Definition of Done: 文件头部与入口函数说明明确其不是仓库生产主口径
  - Blocking: None
- [x] P1: 运行 strict validation 并完成 context 同步
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 通过，`notes/context/*` 指向当前 session
  - Blocking: None

## Parking Lot
- [ ] 若未来接入含 `aggressor/open_close/customer_type` 的供应商字段，重新评估 inventory-based GEX 主口径切换
- [ ] 评估是否需要单独新增一份“数据能力边界”SOP 说明 Longbridge 字段限制

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 新建 session `2026-03-12/gex-oi-wording-sync`（2026-03-12 11:58 ET）
- [x] 完成当前生效 GEX 文案扫描并定位需修正文件（2026-03-12 12:00 ET）
- [x] `scripts/validate_session.ps1 -Strict` 通过并完成 context 同步（2026-03-12 12:03 ET）

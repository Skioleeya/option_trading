# Open Tasks

## Priority Queue
- [x] P0: 产出 LongPort 期权字段精确字典
  - Owner: Codex
  - Definition of Done: 3 个官方页面的字段、类型、枚举和仓库映射全部落到结构化 Markdown
  - Blocking: None
- [x] P1: 完成 session/context 同步并通过 strict gate
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passed
  - Blocking: None
- [ ] P2: 如用户继续推进，补做字段保真差异的集成清单
  - Owner: Codex
  - Definition of Done: 明确哪些官方字段值得补接入，以及哪些封装假设需要 live payload 复核
  - Blocking: 用户后续范围确认

## Parking Lot
- [ ] 对 `trade_status` / `standard` / `contract_multiplier` 做契约保真评估
- [ ] 用 live LongPort payload 核对 `implied_volatility` 的真实格式

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 新建 session `2026-03-12/longport-option-field-dictionary`（2026-03-12 13:06 ET）
- [x] 抓取 3 个官方页面与 `quote/objects.md`（2026-03-12 13:13 ET）
- [x] 新增 `docs/LONGPORT_OPTION_FIELD_DICTIONARY.md`（2026-03-12 13:14 ET）
- [x] `scripts/validate_session.ps1 -Strict` 通过（2026-03-12 13:17 ET）

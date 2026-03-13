# Open Tasks

## Priority Queue
- [x] P0: 抓取 LongPort `llms.txt` 并提取有效字段
  - Owner: Codex
  - Definition of Done: 核心能力、限频、市场覆盖、交易支持、文档入口均落到结构化 Markdown
  - Blocking: None
- [x] P1: 完成 session/context 同步并通过 strict gate
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passed
  - Blocking: None
- [ ] P2: 如用户继续推进，补充字段级下钻文档
  - Owner: Codex
  - Definition of Done: 对 quote/trade/socket 关键页面做更细字段提取
  - Blocking: 用户后续范围确认

## Parking Lot
- [ ] 对 `quote/pull/option-quote.md` 做字段级提取
- [ ] 对 `quote/pull/optionchain-date-strike.md` 做字段级提取

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 新建 session `2026-03-12/longport-llms-fields-doc`（2026-03-12 12:54 ET）
- [x] 抓取并整理 `llms.txt` 有效字段到 `docs/LONGPORT_LLMS_EFFECTIVE_FIELDS.md`（2026-03-12 12:56 ET）
- [x] `scripts/validate_session.ps1 -Strict` 通过（2026-03-12 12:58 ET）

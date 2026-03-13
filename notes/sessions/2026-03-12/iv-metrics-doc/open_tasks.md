# Open Tasks

## Priority Queue
- [x] P0: 盘点当前仓库 IV 相关指标并确认源码出处
  - Owner: Codex
  - Definition of Done: 指标范围覆盖 L1/L2/L3 与 shared 中当前生效的 IV 直接/间接依赖项
  - Blocking: None
- [x] P0: 输出 `docs/IV_METRICS_MAP.md`
  - Owner: Codex
  - Definition of Done: 文档包含 `指标名 | 层级 | 是否直接依赖IV | 公式/来源文件`
  - Blocking: None
- [x] P1: 完成 session/context 同步并通过 strict gate
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passed
  - Blocking: None

## Parking Lot
- [ ] 若未来 inventory-based GEX 成为主口径，补一版按数据能力分层的 IV/GEX 文档
- [ ] 评估是否需要将该文档挂入 `docs/SOP/` fast-load pack

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 新建 session `2026-03-12/iv-metrics-doc`（2026-03-12 12:13 ET）
- [x] 完成 IV 相关指标与源码位置扫描（2026-03-12 12:15 ET）
- [x] 新增 `docs/IV_METRICS_MAP.md`（2026-03-12 12:18 ET）
- [x] `scripts/validate_session.ps1 -Strict` 通过（2026-03-12 12:19 ET）

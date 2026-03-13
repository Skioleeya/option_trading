# Open Tasks

## Priority Queue
- [x] P0: 统一 `total_put_gex` 口径为非负幅度并保持 `net_gex = call - put`（Owner: Codex, Done: 2026-03-12 ET）
- [x] P1: `flip_level` 切换为 cumulative net GEX 首次过零语义（Owner: Codex, Done: 2026-03-12 ET）
- [x] P1: `net_gex_normalized` 归一公式修正为 MMUSD `/1000`（Owner: Codex, Done: 2026-03-12 ET）
- [x] P1: 定向回归（L1/L2）通过（Owner: Codex, Done: 2026-03-12 ET）

## Parking Lot
- [x] None (2026-03-12 ET)

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Updated GEX sign convention across L1 mainline + legacy aggregator (2026-03-12 ET)
- [x] Replaced adjacency sign-change flip with cumulative zero-cross + interpolation (2026-03-12 ET)
- [x] Added extractor scale test and flip-level scenario tests (2026-03-12 ET)

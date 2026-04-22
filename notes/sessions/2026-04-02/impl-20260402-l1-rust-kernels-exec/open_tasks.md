# Open Tasks

## Priority Queue
- [x] P0: 落地 L1 Rust kernels 并保持层边界与契约一致
  - Owner: Codex
  - Definition of Done: `bsm_batch_numpy_tier`、`aggregate_greeks_full`、`select_walls` 上线且 Python 路径显式 fallback。
  - Blocking: none
- [x] P1: 完成 runtime 文件行数治理与测试落地
  - Owner: Codex
  - Definition of Done: 改动的 Python/Rust runtime 文件全部 `<=400` 行；新增 parity tests 全通过。
  - Blocking: none
- [x] P2: 完成 OpenSpec/SOP 同步并准备 strict handoff
  - Owner: Codex
  - Definition of Done: OpenSpec 任务状态更新、SOP 更新、session/context 文档可进入 strict gate。
  - Blocking: none

## Parking Lot
- [x] Item: none

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Runtime Rust kernels + Python fallback integration completed (2026-04-02 16:27 ET)
- [x] `l1_compute/tests` parity suite added and passing (`54 passed`) (2026-04-02 16:19 ET)
- [x] Layer boundary scan passed (2026-04-02 16:21 ET)

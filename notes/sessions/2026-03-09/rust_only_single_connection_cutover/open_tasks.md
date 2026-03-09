# Open Tasks

## Priority Queue
- [x] P0: Rust-only 单连接收敛（移除 Python pre-flight QuoteContext 主路径）。
  - Owner: Codex
  - Definition of Done: `main/container/lifespan` 去除 `primary_ctx` 链路，L0 runtime 默认 `rust_only`。
  - Blocking: 无
- [x] P1: L0 runtime 协议化（subscription/orchestrator/IV/Tier2/Tier3/builder decouple）。
  - Owner: Codex
  - Definition of Done: L0 调度路径不直接依赖 `QuoteContext`，统一经 `L0QuoteRuntime` 调用。
  - Blocking: 无
- [x] P1: Rust FFI 补齐 REST pull + anti-pattern 修正。
  - Owner: Codex
  - Definition of Done: 新增 `rest_quote/rest_option_quote/rest_option_chain_info_by_date/rest_calc_indexes`，修改后的 Rust 运行文件无 `unwrap()`。
  - Blocking: 无
- [x] P2: OpenSpec 父提案+子提案组合落地。
  - Owner: Codex
  - Definition of Done: `1` 父提案 + `3` 子提案目录（proposal/design/tasks/spec）均创建并可追踪依赖。
  - Blocking: 无

## Parking Lot
- [x] Item: None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Rust-only runtime cutover + OpenSpec parent/child bundle (2026-03-09 11:38 ET)

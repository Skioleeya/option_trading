# Open Tasks

## Priority Queue
- [x] P0: 修复 `research_store` 对已退役模块 `shared.system.tactical_triad_logic` 的硬依赖
  - Owner: Codex
  - Definition of Done: `append_tick` 仅调用 Rust owner，不再 import 旧 Python 路径
  - Blocking: None
- [x] P1: 守护测试补齐
  - Owner: Codex
  - Definition of Done: 新增测试断言 `shared_rust_services/src/research_store.rs` 不得出现旧模块路径
  - Blocking: None
- [x] P1: 相关 EOD 源质量守卫回归
  - Owner: Codex
  - Definition of Done: `test_eod_task_guards.py` 与 `test_eod_bucket_guards.py` 全通过
  - Blocking: None
- [x] P1: Cargo target 目录固化与编译验证
  - Owner: Codex
  - Definition of Done: `tmp/cargo_target` 生效且 `shared_rust_services` 的 `cargo check` 通过
  - Blocking: None

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Root cause fixed: `research_store` VRP path no longer depends on removed Python module (2026-04-16 06:29 ET)
- [x] Cargo target dir finalized: `tmp/cargo_target` + compile pass after clearing env override (2026-04-16 06:39 ET)

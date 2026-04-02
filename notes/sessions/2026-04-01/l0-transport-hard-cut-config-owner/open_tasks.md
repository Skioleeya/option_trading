# Open Tasks

## Priority Queue
- [ ] P1: 统一 Python/Rust transport 常量生成链，避免 `shared/contracts` 与 `l0_ingest/l0_rust/src/transport_contract.rs` 双边人工镜像
  - Owner: Codex
  - Definition of Done: transport contract constants single-source 化
  - Blocking: 需要确定生成方式和仓库 owner
- [ ] P1: 为 Rust gateway 显式 config 路径补充更细的 native 单元测试
  - Owner: Codex
  - Definition of Done: `configure()` 和 writer config normalize 在 Rust 层有独立测试
  - Blocking: 需要新增细粒度 test module
- [ ] P2: 评估 `_native_generated/l0_rust.pyd` 的长期交付方式
  - Owner: Codex
  - Definition of Done: 明确生成/分发/加载策略，不再依赖手工 wheel 提取
  - Blocking: 需要决定 CI/packaging 流程

## Parking Lot
- [ ] 为 `shared/services/l0_runtime/l0_rust.py` 补充 SOP 或 build note
- [ ] 为 source runtime adapter 拆更细的 package 边界

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 移除 `openapi_bootstrap.py` 的 LongPort env write bridge (2026-04-01 12:24 ET)
- [x] Rust gateway 改为显式 `configure()` 注入，不再依赖 `Config::from_env()` (2026-04-01 12:24 ET)
- [x] Arrow writer batch/shm/signal config 改为显式输入，不再读 env (2026-04-01 12:24 ET)

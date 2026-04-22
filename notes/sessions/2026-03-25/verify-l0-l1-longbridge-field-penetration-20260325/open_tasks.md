# Open Tasks

## Priority Queue
- [x] P0: 验证纯 Rust L0 -> L1 的 LongPort/Longbridge 关键字段穿透
  - Owner: Codex
  - Definition of Done: targeted tests 覆盖 Arrow roundtrip、fetch snapshot 元数据、L1 ingress/compute 日志
  - Blocking: 已完成
- [x] P1: 为 L1 / Active Options 数据链补诊断日志
  - Owner: Codex
  - Definition of Done: 日志可明确看到 `rust_active/shm_status`、`gex/vanna/charm/svol`、以及 `active_options flow`
  - Blocking: 已完成
- [x] P1: 同步 session/context/handoff 并跑 strict validation
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 全绿，context 指针与 handoff 一致
  - Blocking: 已完成

## Parking Lot
- [ ] 若用户需要真实运行态验活，再启动 backend 并抓取 `logs/backend_runtime.current.log` 中的新诊断标记
- [ ] 若后续需要更细粒度 contract 观测，可把 Active Options top rows 摘要沉到 `/debug/persistence_status`

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `tests/l0_runtime/test_arrow_roundtrip.py tests/l0_runtime/test_option_chain_builder_rust_events.py tests/l0_runtime/test_fetch_chain_components.py l1_compute/tests/test_reactor.py shared/services/active_options/test_input_adapter.py app/loops/tests/test_housekeeping_gpu_dedup.py` 共 47 项通过 (2026-03-25 22:49 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` 全绿通过 (2026-03-25 22:52 ET)
- [x] `L1ComputeReactor` 输出 ingress/compute summary，覆盖 `rust_active/shm_status/source_ts/gex/vanna/charm/atm_iv/svol` (2026-03-25 22:47 ET)
- [x] Active Options 输入覆盖日志与 flow 输出日志已落地，并有 `caplog` 定向测试 (2026-03-25 22:48 ET)

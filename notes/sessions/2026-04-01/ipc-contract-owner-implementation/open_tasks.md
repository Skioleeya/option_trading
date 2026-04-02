# Open Tasks

## Priority Queue
- [ ] P0: 执行 implementation session 的 strict validation 并留痕
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 返回 `Session validation passed.`
  - Blocking: handoff/meta/context 尚未最终同步
- [ ] P1: 在后续 implementation slice 中让 Rust `ipc_writer` 与 Python contract owner 完成 signal owner 对齐
  - Owner: Codex
  - Definition of Done: Rust 和 Python 对 `L0 IPC signal` 都引用统一 owner 语义，环境变量仅作为 override
  - Blocking: 需要下一个 first-wave implementation session
- [ ] P2: 继续 first-wave implementation，把 direct env reads 从 `shared/services/l0_runtime/source/runtime/*` 收口到 config boundary
  - Owner: Codex
  - Definition of Done: `market_data_gateway.py` 等不再直接读取环境变量
  - Blocking: 需要更大的 constants/config implementation slice

## Parking Lot
- [ ] 如需进一步减少硬编码，可在下一 slice 收敛 `SHM_STATUS_OK` 的 Rust 侧镜像 owner。
- [ ] 若后续修改 IPC contract key 名称，必须同步更新 dependency artifact 与相关 SOP/测试。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 完成 L0 IPC signal 与 shm status 的 Python runtime contract owner 收敛，并通过 targeted L0 tests（2026-04-01 11:34 ET）

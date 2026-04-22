# Project State

## Snapshot
- DateTime (ET): 2026-03-19 16:32:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `d64eb98`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`（验活后 `missing_turnover_rows=0`）
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 修复 `quote_runtime -> rust bridge` 链路丢失 `turnover/current_volume`，恢复 Active Options LIVE 信号判定。
- Scope In: `l0_ingest/l0_rust`, `l1_compute/rust_bridge.py`, `l0_ingest/feeds/rust_event_bridge.py`, 相关单测与文档。
- Scope Out: `chain_state_store`/`fetch_chain` 业务逻辑、前端排序逻辑、FLOW 数值算法。

## What Changed (Latest Session)
- Files: Rust SHM schema/ipc/lib、Python bridge、rust event adapter、l0/l1 tests、OpenSpec、字典与 SOP。
- Behavior:
  - SHM v2 事件新增 `current_volume/turnover/current_turnover`。
  - Python bridge 支持 v2 优先 + v1 兼容解包。
  - `parse_rust_event` 映射 flow 字段。
  - `l0_rust` 推送前新增 `non_negative_volume_to_u64`，避免负 volume/curr_volume 符号翻转成超大 u64。
  - WS flow 字段收敛：
    - Rust push 恢复独立透传 `volume=q.volume` 与 `current_volume=q.current_volume`（不互相覆盖）。
    - Store 层新增双字段融合：两者都有效时取较小值作为榜单 `volume`，单字段失真不再污染 Active Options。
- Verification:
  - `test_chain_state_store.py` 11/11 通过（含“双字段一侧损坏”的新增用例）。
  - 桥接链路 pytest 10/10 通过。
  - 运行验活 PASS（`live_rows=4`, `degraded_rows=1`, `missing_gamma_rows=1`, `missing_turnover_rows=0`）。

## Risks / Constraints
- Risk 1: 本机缺失 MSVC linker，无法本地完成 Rust 编译验证。
- Risk 2: 工作区存在大量并行未提交改动，strict 需依赖 session meta 精确归档本次范围。

## Next Action
- Immediate Next Step: 在具备 MSVC linker 的环境补跑 Rust `cargo test` 作为附加环境验收。
- Owner: User

## Scope

- [ ] 关闭 Sub-wave F gate（dual-run 比较证据；当前 BLOCKED_BY_LIVE）
- [ ] 关闭 Sub-wave G gate（完整 l0_runtime 测试套件；当前 fallback 受环境依赖阻塞）
- [x] 更新上游 `impl-20260402-l0-runtime-rust-cutover/tasks.md` 剩余 [ ] 项

## Pre-conditions（执行前确认）

- [x] Sub-wave F runtime blockers 已修复（get_oi_delta + _native_generated 路径，2026-04-02 14:35 ET）
- [x] SPY.US MVP connectivity 通过（2026-04-02 12:44 ET 和 14:18 ET）
- [x] `tmp/pytest_cache` ACL 已修复（2026-04-02，Lenovo icacls /grant + /reset /T /C）
- [x] E2E smoke test PASS（test_l0_l4_pipeline.py，2026-04-02 14:42 ET）

## Implementation

### Step 1 — Sub-wave G 测试套件（先执行，不需要实盘）

- [ ] `pwsh scripts/test/run_pytest.ps1 tests/l0_runtime/` 全通过
  - 如路径不存在，改用：`pwsh scripts/test/run_pytest.ps1 l0_ingest/tests/`
- [ ] 记录通过数量和 warning 数量
  - 2026-04-03 fallback 执行 `python3 scripts/test/test_l0_l4_pipeline.py` 失败：`ModuleNotFoundError: No module named 'websockets'`
  - 2026-04-03 native import fallback 失败：`ImportError: .../shared/services/l0_runtime/_native_generated/wave10/l0_rust.pyd: invalid ELF header`

### Step 2 — Sub-wave F 双运行证据（下一个实盘交易时段）

- [ ] 启动后台，确认 `rust_started=true`：`curl http://127.0.0.1:8001/debug/persistence_status`
- [ ] 确认两个 gateway 同时活跃 ≥ 60 分钟（runtime log）
  - BLOCKED_BY_LIVE: 当前会话不在实盘连续 60 分钟双网关窗口内
- [ ] 抽取 ≥ 10 个同时间戳 EnrichedSnapshot（Python vs Rust）
- [ ] 计算字段相对误差（net_gex/net_vanna/net_charm/call_wall/put_wall）
  - 全部 < 0.01%：记录比较表到 handoff，标记 gate PASS
  - 任一 ≥ 0.01%：记录偏差根因，开新 DEBT，本 gate 延期
- [ ] 将比较表追加到本会话 handoff.md

### Step 3 — 上游 tasks.md 收口

- [ ] 将 `impl-20260402-l0-runtime-rust-cutover/tasks.md` 以下项标为 [x]：
  - `Sub-wave F: dual-run compare evidence recorded in handoff`
  - `Full l0 test suite: pwsh scripts/test/run_pytest.ps1 tests/l0_runtime/`
  - `[x] Record DEBT-NEW, DEBT-CLOSED, DEBT-DELTA in session handoff`
- [ ] 更新 `notes/context/open_tasks.md`：将 l0_runtime neutral-surface 退役相关项标为 [x]

## Verification

- [ ] `pwsh scripts/test/run_pytest.ps1 tests/l0_runtime/` → all pass
  - 2026-04-03 fallback `python3 scripts/test/test_l0_l4_pipeline.py` failed: `ModuleNotFoundError: No module named 'websockets'`
- [ ] Sub-wave F 比较表已记录（handoff）：所有字段相对误差 < 0.01%
  - BLOCKED_BY_LIVE
- [ ] `pwsh scripts/validate_session.ps1 -Strict` → PASS
  - Not runnable in this shell; PowerShell interop unavailable from WSL.
- [x] `python scripts/policy/check_openspec_chain.py` → PASS
  - 2026-04-03 初次失败原因为 `invalid_refactor_change_id`；完成 change-id 规范化与 child 必需文件补齐后，已重跑 PASS。

## DoD

- [ ] Sub-wave F 证据已回填到 handoff（实盘比较表）
- [ ] Sub-wave G 测试套件全通过
- [x] 上游 tasks.md Phase N 全部 [ ] 关闭
- [ ] `notes/context/open_tasks.md` l0_runtime neutral-surface 项标记 [x]
- [ ] DEBT-NEW=0，DEBT-CLOSED=2（F+G gates），DEBT-DELTA=-2
- [ ] strict gate PASS

## Evidence

（待 Codex 执行后回填）

## Notes

OPENSPEC: impl-20260402-l0-runtime-neutral-surface-closeout
PARENT: impl-20260402-l0-runtime-rust-cutover
BLOCKED_BY_LIVE: Sub-wave F 需要下一个实盘交易时段（Step 1 不需要实盘，可立即执行）
ACL_STATUS: tmp/pytest_cache ACL 已修复 2026-04-02；但当前 shell 缺少 `pwsh` 且 fallback 依赖不满足（`websockets` / Windows `.pyd`）

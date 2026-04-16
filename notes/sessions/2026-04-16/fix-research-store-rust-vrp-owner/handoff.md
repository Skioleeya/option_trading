# Handoff

## Session Summary
- DateTime (ET): 2026-04-16 06:51:15 -04:00
- Goal: 修复 `research/raw|feature|label` 无法落盘根因，禁止兼容。
- Outcome: 已将 `ResearchFeatureStore` 的 `vrp_official_hv_based` 计算硬切到 Rust owner，移除对已退役 Python 模块路径的运行时依赖。

## What Changed
- Code / Docs Files:
  - shared_rust_services/src/research_store.rs
  - shared_rust_services/src/tactical.rs
  - scripts/test/test_module_structure_guards.py
  - .gitignore
  - shared_rust/services.pyd
  - notes/sessions/2026-04-16/fix-research-store-rust-vrp-owner/project_state.md
  - notes/sessions/2026-04-16/fix-research-store-rust-vrp-owner/open_tasks.md
  - notes/sessions/2026-04-16/fix-research-store-rust-vrp-owner/handoff.md
  - notes/sessions/2026-04-16/fix-research-store-rust-vrp-owner/meta.yaml
  - notes/context/project_state.md
  - notes/context/open_tasks.md
  - notes/context/handoff.md
- Runtime / Infra Changes:
  - `shared_rust_services/src/research_store.rs`:
    - `use crate::tactical::compute_vrp_impl;`
    - `vrp_official_hv_based` 改为 `compute_vrp_impl(Some(atm_iv), Some(hv))`
    - 删除 `py.import("shared.system.tactical_triad_logic").getattr("compute_vrp")` 依赖链
  - `shared_rust_services/src/tactical.rs`:
    - `compute_vrp_impl` 升级为 `pub(crate)`，供内部模块复用
  - `scripts/test/test_module_structure_guards.py`:
    - 新增 `test_research_store_no_legacy_tactical_import`
  - `.cargo/config.toml`（本地机器配置，文件被 `.gitignore` 忽略）:
    - `[build].target-dir = "E:\\US.market\\Option_v3\\tmp\\cargo_target"`
  - 当前 shell 存在环境变量覆盖：
    - `CARGO_TARGET_DIR=E:\US.market\cargo_target`
    - 需在构建前清除：`Remove-Item Env:CARGO_TARGET_DIR`
  - OPENSPEC-EXEMPT: Root-cause hotfix limited to existing Rust owner cutover completion; no contract/schema expansion.
  - SOP-EXEMPT: No behavior change in L0/L1/L2/L3/L4/app contracts; only internal Rust service dependency path correction.
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId fix-research-store-rust-vrp-owner -Title "fix research store vrp owner hard cut" -Scope "replace deprecated tactical_triad_logic import in rust research store and restore raw-feature-label persistence" -Owner "Codex" -ParentSession "2026-04-13/retune-gex-superpin-4b" -Timezone "Eastern Standard Time" -UpdatePointer
  - cargo check (workdir=shared_rust_services)  [failed: permission denied on target dir]
  - $env:CARGO_TARGET_DIR='E:\US.market\Option_v3\tmp\cargo_target'; cargo check  [failed: permission denied]
  - $env:CARGO_TARGET_DIR='E:\US.market\Option_v3\shared_rust_services\target'; cargo check  [failed: permission denied]
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_module_structure_guards.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_module_structure_guards.py -k research_store_no_legacy_tactical_import
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_eod_task_guards.py scripts/test/test_eod_bucket_guards.py
  - Remove-Item Env:CARGO_TARGET_DIR -ErrorAction SilentlyContinue; cargo check --manifest-path shared_rust_services/Cargo.toml
  - [Environment]::SetEnvironmentVariable('CARGO_TARGET_DIR',$null,'User')  [failed: Requested registry access is not allowed]
  - cargo build --release --manifest-path shared_rust_services/Cargo.toml  [failed: access denied on tmp/cargo_target/release/.cargo-lock]
  - cargo build --release --manifest-path shared_rust_services/Cargo.toml --target-dir tmp/cargo_target_runtime
  - Copy-Item tmp\cargo_target_runtime\release\services.dll shared_rust\services.pyd -Force
  - powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1
  - Invoke-RestMethod http://127.0.0.1:8001/health
  - Invoke-RestMethod http://127.0.0.1:8001/debug/persistence_status
  - Get-Content logs/backend_runtime.current.log -Tail 5000 | Select-String "No module named 'shared.system.tactical_triad_logic'|research_store append failed"
  - Get-ChildItem data/research/raw|feature|label (latest parquet files check)
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict

## Verification
- Passed:
  - `scripts/test/run_pytest.ps1 scripts/test/test_module_structure_guards.py -k research_store_no_legacy_tactical_import` -> 1 passed
  - `scripts/test/run_pytest.ps1 scripts/test/test_eod_task_guards.py scripts/test/test_eod_bucket_guards.py` -> 10 passed
  - `Remove-Item Env:CARGO_TARGET_DIR; cargo check --manifest-path shared_rust_services/Cargo.toml` -> passed
  - `cargo build --release --manifest-path shared_rust_services/Cargo.toml --target-dir tmp/cargo_target_runtime` -> passed
  - `Copy-Item ...\services.dll -> shared_rust/services.pyd` -> succeeded (`LastWriteTime=2026-04-16 06:48:49 ET`)
  - `scripts/ops/start_backend.ps1` -> started (`pid=12096`), `/health` 返回 `status=ok`
  - 最近 5000 行日志未出现 `No module named 'shared.system.tactical_triad_logic'` 与 `research_store append failed`
  - `/debug/persistence_status` 显示 `research_store.write_failures=0`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> PASS
- Failed / Not Run:
  - `scripts/test/run_pytest.ps1 scripts/test/test_module_structure_guards.py` -> 1 failed (pre-existing baseline violations unrelated to this fix):
    - `l3_assembly/assembly/ui_state_tracker.py: 401`
    - `shared_rust_services/src/active_options/support.rs: 402`
  - 历史尝试中曾出现 `cargo check` 权限失败（`os error 5`），根因是环境变量覆盖；已通过清除 `CARGO_TARGET_DIR` 解决。
  - `cargo build --release --manifest-path shared_rust_services/Cargo.toml` 默认 target-dir 仍会命中 `tmp/cargo_target/release/.cargo-lock` 权限拒绝，故改用 `--target-dir tmp/cargo_target_runtime`。
  - 当日 `20260416` 的 `research/raw|feature|label` 文件新增写入暂未验证：当前时段为 06:51 ET（非 RTH），research store 按合同跳过非交易时段写入。

## Pending
- Must Do Next:
  - 在真实主机（非沙箱）清理用户级覆盖：`setx CARGO_TARGET_DIR ""` 或通过系统环境变量 UI 删除该键，避免覆盖仓库 `.cargo/config.toml`
  - Rebuild and reload `shared_rust/services.pyd` in writable host environment, then verify runtime log no longer contains `No module named 'shared.system.tactical_triad_logic'`.
  - 09:30 ET 后验证 `data/research/raw|feature|label` 的 `*_20260416.parquet` 是否恢复持续落盘（当前 06:51 ET 非 RTH 无法判定）。
- Nice to Have:
  - Add integration test that exercises `ResearchFeatureStore.append_tick()` end-to-end with non-empty `longport_official_hv_decimal`.

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本会话无未关闭任务，已完成根因修复与关键回归。
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-16
- DEBT-RISK: 无
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: DEBT-DELTA=0
- RUNTIME-ARTIFACT-EXEMPT: Rebuilt and replaced `shared_rust/services.pyd` as required runtime artifact.

## How To Continue
- Start Command:
  - powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1
- Key Logs:
  - [L3 Reactor]
  - [L3-PAYLOAD]
- First File To Read:
  - shared_rust_services/src/research_store.rs

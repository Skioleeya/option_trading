# AGENT.md: Quant Desk Standard Operating Procedures (SOP)
> **"We are not here to build a retail app. We are here to capture institutional flow before the market prices it in."** — *Lead Quant Architect*

Welcome to the SPY 0DTE Options Dashboard project. This document defines irreversible engineering constraints for all agents.
---
## 1. Architectural Mandates (Non-Negotiable)
### 1.1 Rust-Python Hybrid Performance
Python gives agility; **Rust gives deterministic speed**.
* **Zero-Copy IPC**: L0→L1 data MUST use Apache Arrow RecordBatches over SHM.
* **No Pure Python Full-Chain Loops**: Chain-wide Greeks/GEX logic MUST be Rust/CuPy vectorized.
* **GIL Sovereignty**: Heavy Python compute MUST be offloaded via `asyncio.to_thread`.

### 1.2 Resilience & Self-Healing
* **SHM Handshake**: Shared resources MUST follow Create-or-Open (see `l0_rust/src/lib.rs`).
* **No Silent Failures**: No Rust `unwrap()` in runtime path; no silent Python `try-except`.
* **Cascading Fallback**: Rust path failure MUST relay to Python stable path without dropping L4 broadcast.

### 1.3 Schema & Contract Integrity
* **Strict Alignment**: `CleanQuoteEvent` / `EnrichedSnapshot` changes MUST be synchronized across Rust/Python.
* **Metadata Continuity**: `rust_active`, `shm_stats` and diagnostics MUST survive L0→L4 propagation.
---
## 2. Microstructure & Quant Principles
### 2.1 Native Threat Pipeline
* **Early Bound**: OFII and Sweep detection MUST be computed as close to wire as possible (L0 Rust).
* **Greeks Sovereignty**: Do not trust broker Greeks; compute Delta/Gamma/Vanna/Charm locally (BSM/SABR).

### 2.2 Anti-Oscillation (No Ping-Pong)
* **State Damping**: Use EWMA smoothing or threshold hysteresis.
* **Exit Discipline**: Every decision rule MUST define anti-flicker exit behavior.
---
## 3. Engineering Rigor & Observability
### 3.1 Structured Observability
* **Reactor Logging**: L0-L3 MUST use standard markers (e.g., `[Debug] L0 Fetch`, `[L3 Assembler]`).
* **Performance Telemetry**: If L1 lags L0 by > 5 IPC ticks, system MUST enter `STALLED`.

### 3.2 Gold Context Initialization
* **SDK Safety**: Initialize Longport SDK in PRE-FLIGHT via `AppContainer` DI to avoid C-level deadlocks.
---
## 4. Development Workflow (OpenSpec Mandate)
1. **Ideate (`/opsx-explore`)**: Deep-dive HFT requirements before coding.
2. **Propose (`/opsx-propose`)**: Define architecture, contracts, and verification plan.
3. **Execute (`/opsx-apply`)**: TDD-first, Rust-first performance, async safety.
4. **Verify**: Fixes MUST pass end-to-end `test_l0_l4_pipeline.py`.
5. **Archive (`/opsx-archive`)**: Merge only after stress-test validation.

### 4.1 Test Execution & Cache Isolation (2026-03-06)
* **Single Entry**: All `pytest` runs MUST use `scripts/test/run_pytest.ps1`.
* **Context Purity**: Do NOT run tests in Administrator context.
* **Cache Isolation**: Cache path MUST be `tmp/pytest_cache` (via `pytest.ini`).
* **Artifact Hygiene**: `pytest-cache-files-*` are permission-failure residue; treat as ops cleanup, never code changes.

Failure to follow these SOPs puts institutional capital at risk. Code with quant rigor; execute with Rust speed.
---
## 5. Incident Addendum: ATM Decay Anchor Integrity (2026-03-06)
### 5.1 Opening Anchor Consistency Before Lock
* **Strict Lock Gate**: `OPENING ATM` MUST NOT lock until spot stability gate passes (min samples + bounded range).
* **Source Consistency Gate**: Validate `spot_nearest_strike` vs `parity_strike`; large divergence blocks lock.
* **No Forced Early Lock**: Early open window prefers `PENDING` over wrong lock.

### 5.2 Persisted Anchor Recovery Validation
* **Mandatory Distance Check**: Restored anchor MUST satisfy `abs(anchor_strike - spot) <= max_distance`.
* **Spot-Unavailable Rule**: If startup spot invalid/unavailable, persisted anchor MUST be skipped in strict mode.
* **Forensic Logging**: Every discard path MUST log date/strike/spot/distance/threshold.

### 5.3 Separation of Concerns
* **Module Boundary**: Split ATM decay into `tracker`, `anchor`, `storage`, `models/helpers`.
* **No Leakage**: `anchor` stays pure logic (no I/O); `storage` stays persistence-only (no strategy logic).
* **Compatibility First**: Preserve legacy imports via shim/re-export during migration.

### 5.4 Delivery Discipline
* **Scope Declaration**: Incident proposal MUST state `hotfix only` or `hotfix + modularization`.
* **Single-Pass Preference**: If modular debt is known high-risk, include it in approved change set.
* **Verification Contract**: ATM anchor changes MUST pass tracker unit tests + L1 reactor regression.
---
## 6. Cross-Dialogue Handoff Contract (Mandatory)
Every agent MUST follow the `notes/context` continuity contract.

### 6.1 Mandatory Context Files
* `notes/context/project_state.md`
* `notes/context/open_tasks.md`
* `notes/context/handoff.md`
* `notes/sessions/YYYY-MM-DD/<task-id>/project_state.md`
* `notes/sessions/YYYY-MM-DD/<task-id>/open_tasks.md`
* `notes/sessions/YYYY-MM-DD/<task-id>/handoff.md`
* `notes/sessions/YYYY-MM-DD/<task-id>/meta.yaml`

### 6.1.1 Mandatory Architecture Fast-Load Pack
* `docs/SOP/SYSTEM_OVERVIEW.md`
* `docs/SOP/L0_DATA_FEED.md`
* `docs/SOP/L1_LOCAL_COMPUTATION.md`
* `docs/SOP/L2_DECISION_ANALYSIS.md`
* `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
* `docs/SOP/L4_FRONTEND.md`

### 6.2 Start-of-Session Rule (Read First)
* **Read Before Any Change**: Read the three `notes/context` index files first.
* **Follow Active Pointer**: Open the active session path referenced by index files.
* **State Alignment**: If notes and repo reality differ, reconcile notes first, then implement.

### 6.2.1 Session Creation Rule (One Change Set, One Folder)
* **Dedicated Session Required**: Use either:
  * `notes/sessions/YYYY-MM-DD/<task-id>/` (default)
  * `notes/sessions/YYYY-MM-DD/HHMM/<task-id>/` (time-bucket mode)
* **Task ID Convention**: `<task-id>` SHOULD follow `HHMM_<scope>_<hotfix|mod|feature>`.
* **No History Overwrite**: Completed session folders are immutable and MUST NOT be repurposed.

### 6.2.2 New-Agent Context Load Checklist
1. Execute Section **6.2**.
2. Read active session `project_state.md`, `open_tasks.md`, `handoff.md`, `meta.yaml`.
3. Execute Section **6.1.1** (all six `docs/SOP` files).
4. Perform reality check (`git status`, branch, key files); reconcile notes first if mismatch.
5. Follow Section **4.1** for pytest entry/context/cache rules.
6. Close by following Sections **6.3** and **6.5**.

### 6.3 End-of-Session Rule (Write Back)
* **Session-local `project_state.md` MUST update**: branch/commit, scope change log, current risks, immediate next action.
* **Session-local `open_tasks.md` MUST update**: `P0/P1/P2` status, owner, DoD, blockers.
* **Session-local `handoff.md` MUST update**: goal/outcome, files changed, commands run, verification, exact next step.
* **Session-local `meta.yaml` MUST update**: `branch`, `base_commit`, `head_commit`, `commands`, `tests_passed`, `tests_failed`.
* **Context Index MUST update**: `notes/context/*.md` MUST point to the current active session.

### 6.4 Commit Discipline
* **Context Is Source of Truth**: Session files + context index SHOULD be committed with delivery.
* **No Silent Exit**: Agents MUST NOT end substantive sessions without handoff-state updates.

### 6.5 Scripted Enforcement
* **Bootstrap Script**: SHOULD use `scripts/new_session.ps1`.
* **Validation Script**: SHOULD run `scripts/validate_session.ps1` before handoff/exit.
* **Validation Scope**: Pointer consistency for active session; structural validity minimum for non-active sessions.

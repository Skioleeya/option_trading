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

### 1.4 Layer Dependency Direction (Hard Gate)
* **One-Way Flow Only**: Allowed runtime dependency direction is `L0 -> L1 -> L2 -> L3 -> L4`; `app/` is orchestration-only wiring, not business logic sink.
* **L2 Isolation**: `l2_decision/` MUST NOT import `l3_assembly/` or `l4_ui/`.
* **L3 Contract-Only L2 Access**: `l3_assembly/` may consume `l2_decision.events/*` contracts only; importing `l2_decision.signals/*`, `l2_decision.agents/*`, or other implementation modules is forbidden.
* **Presenter Purity**: `l3_assembly/presenters/ui/*` MUST NOT import `l1_compute.analysis/*` or `l1_compute.trackers/*`; upstream data enters through `EnrichedSnapshot`/`DecisionOutput` only.
* **No Private-Member Orchestration**: `app/loops/*` MUST NOT touch cross-layer private members (e.g. `obj._active_options_presenter`); use explicit public APIs/adapters.
* **Boundary Adapter Rule**: Cross-layer reuse MUST flow through dedicated contract or neutral service modules; direct implementation imports across non-adjacent layers are forbidden.
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
* **Validation Script**: SHOULD run `scripts/validate_session.ps1 -Strict` before handoff/exit.
* **Architecture Boundary Policy**: `scripts/validate_session.ps1` MUST enforce anti-coupling rules from `scripts/policy/layer_boundary_rules.json` against `meta.yaml.files_changed` runtime source files.
* **Violation Contract**: Any boundary hit MUST fail validation and print offending `file:line`.
* **Validation Scope**: Pointer consistency for active session; structural validity minimum for non-active sessions.

---
## 7. SOP Documentation Sync Contract (Mandatory)
All agents MUST synchronize `docs/SOP` when behavior-level changes are delivered.

### 7.1 Trigger Conditions (Any = Required)
* Runtime or contract changes in `l0_ingest/`, `l1_compute/`, `l2_decision/`, `l3_assembly/`, `l4_ui/`, or `app/`.
* Cross-layer field mapping/name/semantics changes (for example `atm_iv -> spy_atm_iv`, version/timestamp semantics).
* Hotfixes that alter live behavior, fallback behavior, or diagnostics behavior.

### 7.2 Definition of Done
* At least one relevant file under `docs/SOP/*.md` MUST be updated in the same change set.
* Session `handoff.md` MUST list the updated SOP files.
* Without SOP sync (or explicit exemption), the task is NOT complete.

### 7.3 Strict Exemption
* Allowed only for non-behavioral changes (tests/comments/formatting/refactor with no runtime effect).
* `handoff.md` MUST include `SOP-EXEMPT: <reason>` for exemption to be valid.

### 7.4 Validation Gate
* `scripts/validate_session.ps1` SHOULD enforce this contract using session `meta.yaml` + `handoff.md`.
* If trigger conditions are met but no `docs/SOP` update and no `SOP-EXEMPT`, validation MUST fail.

---
## 8. Technical Debt Zero-Tolerance Contract (Mandatory)
All agents MUST treat unclosed debt as delivery risk, not documentation noise.

### 8.1 No Deferred Debt by Default
* Unchecked items in `open_tasks.md` are considered active debt and block clean handoff by default.
* Parking Lot is not an escape hatch; deferred items still count as debt unless explicitly exempted.

### 8.2 Debt Exemption Record (Strict)
If any unchecked item remains, `handoff.md` MUST include all fields:
* `DEBT-EXEMPT: <reason>`
* `DEBT-OWNER: <owner>`
* `DEBT-DUE: YYYY-MM-DD`
* `DEBT-RISK: <risk>`

Missing any field invalidates handoff.

### 8.3 SLA by Priority
* `P0` debt due date MUST be today (same trading day).
* `P1` debt due date MUST be within 2 calendar days.
* `P2` debt due date MUST be within 5 calendar days.
* Overdue debt MUST fail validation.

### 8.4 Single Debt Source of Truth
* Cross-session debt inventory MUST be maintained in `notes/context/open_tasks.md`.
* Session-local unchecked items MUST either:
  * be migrated into global backlog, or
  * be tagged with supersede marker on old records.

### 8.5 Superseded Debt Hygiene
* If a historical debt is resolved by a later session, old task records MUST include:
  * `SUPERSEDED-BY: <session-id>` (or legacy typo-compatible `SUPSERSEDED-BY`).
* Duplicate unresolved debt across sessions without supersede marker MUST fail validation.

### 8.6 Mandatory Debt Metrics
Each `handoff.md` MUST include:
* `DEBT-NEW: <int>`
* `DEBT-CLOSED: <int>`
* `DEBT-DELTA: <int>` where `DEBT-DELTA = DEBT-NEW - DEBT-CLOSED`
* If `DEBT-DELTA > 0`, `DEBT-JUSTIFICATION: <reason>` is mandatory.

### 8.7 Scripted Enforcement
* `scripts/validate_session.ps1` MUST enforce Sections 8.2 / 8.3 / 8.5 / 8.6 for active session handoff.
* Sessions failing debt gate are not delivery-complete and SHOULD NOT be pushed.

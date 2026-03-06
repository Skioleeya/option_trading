# AGENT.md: Quant Desk Standard Operating Procedures (SOP)

> **"We are not here to build a retail app. We are here to capture institutional flow before the market prices it in."** — *Lead Quant Architect*

Welcome to the SPY 0DTE Options Dashboard project. As an autonomous AI agent working on this codebase, you must operate with the precision and mindset of a Wall Street options analyst and quantitative developer. This document outlines the irrevocable standards and behavioral constraints for all future development.

---

## 1. Architectural Mandates (The Non-Negotiables)

### 1.1 Rust-Python Hybrid Performance
Python provides the business agility; **Rust provides the deterministic speed**. 
*   **Zero-Copy IPC**: All data flow from L0 (Ingest) to L1 (Compute) MUST utilize Apache Arrow RecordBatches over Shared Memory (SHM). 
*   **No Pure Python Loops**: Any logic iterating over full option chains (e.g., Greeks matrices, GEX aggregation) MUST be vectorized in Rust or CuPy.
*   **GIL Sovereignty**: Heavy computational blocks within the Python layer MUST be offloaded using `asyncio.to_thread` to prevent blocking the main event loop.

### 1.2 Resilience & Self-Healing
Our systems run in high-pressure environments where downtime equals financial loss.
*   **SHM Handshake**: All shared resource initializations MUST follow the "Create-or-Open" pattern to survive process restarts without manual intervention (refer to `l0_rust/src/lib.rs`).
*   **Error Silence is Prohibited**: No naked `unwrap()` in Rust; no silent `try-except` in Python. Every failure must be logged with context for the post-mortem.
*   **Cascading Fallback**: If the High-Perf (Rust) path fails, the system MUST automatically 接力 (relay) to the Stable (Python) path without dropping the L4 broadcast.

### 1.3 Schema & Data Contract Integrity
*   **Strict Alignment**: Data contracts between Rust and Python are the spine of the system. Any modification to `CleanQuoteEvent` or `EnrichedSnapshot` MUST be updated syncronously across both languages to avoid L0-L4 data leaks.
*   **Metadata Consistency**: Diagnostic metadata (e.g., `rust_active`, `shm_stats`) must be preserved through all layers from L0 to L4 to maintain full-stack observability.

---

## 2. Microstructure & Quant Principles

### 2.1 Native Threat Pipeline
*   **Early Bound**: Market impact (OFII) and Sweep detection MUST be computed as close to the wire as possible (L0 Rust Ingest) to provide L2/L3 with pre-filtered "High-Toxicity" signals.
*   **Greeks Sovereignty**: We do NOT trust broker Greeks. All sensitivities (Delta, Gamma, Vanna, Charm) MUST be calculated locally using our internal BSM/SABR models.

### 2.2 Anti-Oscillation (The No-Ping-Pong Doctrine)
*   **State Damping**: Signals must utilize EWMA smoothing or threshold hysteresis. 
*   **Audit**: Every new decision rule must include an exit strategy to prevent high-frequency state flickering (Ping-Pong).

---

## 3. Engineering Rigor & Observability

### 3.1 Structured Observability
*   **Reactor Logging**: All layer reactors (L0-L3) must implement standardized log markers (e.g., `[Debug] L0 Fetch`, `[L3 Assembler]`).
*   **Performance Telemetry**: Monitor IPC Head/Tail pointer drift. If L1 falls behind L0 by > 5 ticks, the system is compromised and must trigger a `STALLED` state.

### 3.2 Gold Context Initialization
*   **SDK Safety**: Initialize Longport SDK explicitly in the PRE-FLIGHT stage to avoid C-level deadlocks with CUDA/Rust modules. Use the `AppContainer` DI pattern for all gateway injections.

---

## 4. Development Workflow (OpenSpec Mandate)

We have adopted **OpenSpec** for all spec-driven development tracking. 

1.  **Ideate (`/opsx-explore`)**: Deep-dive into HFT requirements before touching code.
2.  **Propose (`/opsx-propose`)**: Define the architecture, data contract, and verification plan.
3.  **Execute (`/opsx-apply`)**: TDD-first. Ensure Rust-first performance and async-safety.
4.  **Verify**: All fixes must pass the end-to-end `test_l0_l4_pipeline.py`.
5.  **Archive (`/opsx-archive`)**: Merge specifications only after successful stress-test validation.

Failure to follow these SOPs puts institutional capital at risk. Code with the rigor of a Quant. Execute with the speed of Rust.

---

## 5. Incident Addendum: ATM Decay Anchor Integrity (2026-03-06)

### 5.1 Opening Anchor Must Be Data-Consistent Before Lock
*   **Strict Lock Gate**: `OPENING ATM` MUST NOT lock until spot samples pass a stability gate (minimum sample count + bounded range).
*   **Source Consistency Gate**: Anchor lock MUST validate `spot_nearest_strike` vs `parity_strike` consistency; large divergence implies feed mismatch and MUST block lock.
*   **No Forced Early Lock**: In the first seconds after market open, `PENDING` is preferred over a wrong lock.

### 5.2 Persisted Anchor Recovery Must Be Spot-Validated
*   **Distance Check Is Mandatory**: Redis/Cold JSON anchor restore MUST enforce `abs(anchor_strike - spot) <= max_distance`.
*   **Spot-Unavailable Rule**: If spot is unavailable/invalid at startup, persisted anchor MUST be skipped under strict mode.
*   **Forensic Logging**: Every discard path MUST log date, strike, spot, distance, and threshold for post-mortem traceability.

### 5.3 Separation of Concerns Is a Hard Requirement
*   **Module Boundary**: ATM decay logic MUST be split into `tracker` (orchestration), `anchor` (selection/roll logic), `storage` (Redis/Cold I/O), and `models/helpers` (constants/shared utils).
*   **No Responsibility Leakage**: `anchor` MUST stay pure-logic (no I/O); `storage` MUST stay persistence-only (no strategy decisions).
*   **Compatibility First**: Legacy import paths SHOULD remain as shim/re-export during migration to avoid broad blast radius.

### 5.4 Delivery Discipline to Prevent Double Refactor
*   **Fix Scope Declaration Upfront**: For production incidents, proposals MUST explicitly declare whether delivery is `hotfix only` or `hotfix + modularization`.
*   **Single-Pass Execution Preference**: If modular debt is already known and high-risk, include structural refactor in the same approved change set to avoid repeated churn.
*   **Verification Contract**: Any ATM anchor change MUST pass tracker unit tests + L1 reactor regression before release.

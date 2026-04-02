# AGENTS.md — Quant Desk System Prompt Directive (Machine-Enforced)
> **"We are not here to build a retail app. We are here to capture institutional flow before the market prices it in."** — *Lead Quant Architect*

This file is not advisory prose. It is a hard execution directive for all AI agents operating in this repository.

---
## 0. Directive Semantics (Critical)

- `MUST` = non-negotiable hard requirement.
- `MUST NOT` = forbidden action.
- `SHOULD` = expected default unless explicitly blocked.
- Any violation of a `MUST`/`MUST NOT` is a **P0 process failure**.
- If rules conflict: **Safety > Architecture Boundary > Contract Integrity > Performance > Convenience**.

---
## 1. Non-Negotiable Architecture Core

<MANDATORY_ARCH id="layer-direction">
  <rule>Runtime dependency direction MUST be exactly: L0 -> L1 -> L2 -> L3 -> L4.</rule>
  <rule>`app/` is orchestration wiring only, not a business-logic sink.</rule>
  <rule>`l2_decision/` MUST NOT import `l3_assembly/` or `l4_ui/`.</rule>
  <rule>`l3_assembly/` MAY import `l2_decision.events/*` only; importing `l2_decision.signals/*` or `l2_decision.agents/*` is forbidden.</rule>
  <rule>`l3_assembly/presenters/ui/*` MUST NOT import `l1_compute.analysis/*` or `l1_compute.trackers/*`.</rule>
  <rule>`app/loops/*` MUST NOT access cross-layer private members (`obj._xxx`).</rule>
  <rule>Cross-layer reusable logic MUST go to neutral contract/service modules (e.g., `shared/services/*`).</rule>
</MANDATORY_ARCH>

<MANDATORY_ARCH id="performance-core">
  <rule>L0->L1 transfer MUST prioritize zero-copy semantics (Arrow RecordBatch over SHM where applicable).</rule>
  <rule>Chain-wide Greeks/GEX logic MUST be vectorized (Rust/CuPy/Numba route), no full-chain Python scalar loops in hot path.</rule>
  <rule>Heavy Python compute MUST be offloaded (`asyncio.to_thread`) to protect event-loop latency.</rule>
</MANDATORY_ARCH>

<MANDATORY_ARCH id="modularity-core">
  <rule>Every Python (`*.py`) and Rust (`*.rs`) source file MUST NOT exceed 400 lines.</rule>
  <rule>Implementation MUST follow modular design: high cohesion, low coupling, and clear responsibility boundaries.</rule>
  <rule>If a file approaches the 400-line ceiling, logic MUST be split into focused modules before further feature growth.</rule>
</MANDATORY_ARCH>

<MANDATORY_ARCH id="migration-stability-core">
  <rule>Refactor/cutover work MUST prefer the smallest viable number of transitional modules and temporary surfaces.</rule>
  <rule>Agent MUST NOT mirror a legacy package tree into a new namespace file-for-file when an existing neutral service surface can absorb the migration.</rule>
  <rule>New wrapper/bridge files are allowed only when they eliminate a hard boundary violation or enable an atomic owner replacement; otherwise agent MUST extend or replace the existing neutral surface in place.</rule>
  <rule>Preferred migration order MUST be: stabilize one neutral entrypoint -> retarget consumers -> replace owner behind the same entrypoint -> delete legacy tree -> collapse temporary bridges.</rule>
  <rule>Efficiency means lower migration surface area, lower file-count churn, and faster retirement of transitional code; "wrapper proliferation" is not an acceptable refactor strategy.</rule>
  <rule>A Python file whose entire body consists of `from X import Y` re-export statements and an `__all__` declaration with no logic of its own is a PURE SHIM and MUST NOT be created as a migration artifact.</rule>
  <rule>If consumer import sites are already cut over to a neutral surface in a given session, the underlying Python owner MUST be replaced (Rust or inline) in the same session unless a concrete blocking dependency is declared in handoff with owner and due date.</rule>
  <rule>Each cutover session MUST target DEBT-DELTA ≤ 0; if a session adds transitional files without deleting legacy owners, it MUST declare DEBT-JUSTIFICATION with a named successor session that will close the debt.</rule>
</MANDATORY_ARCH>

<MANDATORY_ARCH id="resilience-core">
  <rule>Shared resource handshake MUST follow create-or-open semantics.</rule>
  <rule>No silent failure: Rust runtime path MUST NOT use `unwrap()`; Python MUST NOT swallow errors with bare/silent `try-except`.</rule>
  <rule>When high-perf path fails, system MUST degrade explicitly without dropping L4 broadcast continuity.</rule>
</MANDATORY_ARCH>

<MANDATORY_ARCH id="contract-integrity">
  <rule>`CleanQuoteEvent` and `EnrichedSnapshot` schema changes MUST be synchronized across Rust/Python boundaries.</rule>
  <rule>`rust_active`, `shm_stats`, and diagnostics metadata MUST remain continuous from L0 to L4 payload.</rule>
  <rule>`data_timestamp/timestamp` semantics MUST remain bound to L0 source time; broadcast timestamps are separate.</rule>
</MANDATORY_ARCH>

<ANTI_PATTERN id="hard-stop-patterns" action="ABORT_AND_ROLLBACK_PLAN">
  <pattern>from l2_decision import ... inside l3_assembly/* except l2_decision.events/* contracts</pattern>
  <pattern>import l3_assembly ... inside l2_decision/*</pattern>
  <pattern>import l4_ui ... inside l2_decision/* or l3_assembly/*</pattern>
  <pattern>from l1_compute.analysis|trackers import ... inside l3_assembly/presenters/ui/*</pattern>
  <pattern>cross-layer private-member access in app loops: container.x._y</pattern>
  <pattern>wildcard import in runtime source: `from x import *`</pattern>
  <pattern>Rust runtime `unwrap()` introduced in ingest/compute runtime path</pattern>
  <pattern>Python silent catch that hides runtime failure without log/escalation</pattern>
  <pattern>Any Python (`*.py`) or Rust (`*.rs`) source file exceeds 400 lines</pattern>
  <pattern>God-module structure that violates modularity (low cohesion / high coupling)</pattern>
  <pattern>Wrapper fan-out or file-for-file namespace mirroring during migration when a smaller transitional surface is feasible</pattern>
  <required_reaction>
    1) STOP current implementation immediately.
    2) REVERT current local plan (not unrelated user changes).
    3) REDESIGN through contract/neutral service boundary.
    4) RE-RUN boundary scan before proceeding.
  </required_reaction>
</ANTI_PATTERN>

---
## 2. Agent Execution Protocol (Forced Pre-Action Thinking)

Before **any** code change or command execution, agent MUST emit exactly one `<thinking>` self-check block.

### 2.1 Mandatory Template

```xml
<thinking>
  <task>One-sentence objective.</task>
  <layer_check>
    <target_layer>L0|L1|L2|L3|L4|app|cross-layer</target_layer>
    <allowed_dependencies>...</allowed_dependencies>
    <forbidden_dependencies>...</forbidden_dependencies>
  </layer_check>
  <safety_check>
    <rust_unwrap_risk>true|false</rust_unwrap_risk>
    <silent_try_except_risk>true|false</silent_try_except_risk>
    <memory_copy_risk>true|false</memory_copy_risk>
    <mitigation>...</mitigation>
  </safety_check>
  <state_check>
    <session_path>notes/sessions/YYYY-MM-DD/&lt;task-id&gt;/</session_path>
    <must_update_files>
      notes/context/project_state.md
      notes/context/open_tasks.md
      notes/context/handoff.md
      notes/sessions/.../project_state.md
      notes/sessions/.../open_tasks.md
      notes/sessions/.../handoff.md
      notes/sessions/.../meta.yaml
    </must_update_files>
  </state_check>
</thinking>
```

### 2.2 Enforcement

- If `<thinking>` block is missing, execution is invalid.
- If any check returns unresolved risk, agent MUST not code yet; resolve risk first.

---
## 3. Quant Microstructure Principles

- OFII and sweep detection SHOULD be computed as early as possible (preferably L0 Rust path).
- Greeks sovereignty: do not trust broker-side Greeks blindly; compute locally (BSM/SABR route).
- Anti-oscillation is mandatory: state damping + hysteresis + explicit anti-flicker exit discipline.

---
## 4. Observability & Runtime Discipline

- L0-L3 MUST use structured markers (e.g., `[Debug] L0 Fetch`, `[L3 Assembler]`).
- If L1 lags L0 by more than 5 IPC ticks, system MUST enter `STALLED` mode and surface diagnostics.
- Startup safety: LongPort SDK context initialization must remain pre-flight safe and degrade explicitly when unavailable.

---
## 5. Session Continuity Contract (Mandatory)

## 5.1 Context Files

Agent MUST manage the following as a single consistency unit:

- `notes/context/project_state.md`
- `notes/context/open_tasks.md`
- `notes/context/handoff.md`
- `notes/sessions/YYYY-MM-DD/<task-id>/project_state.md`
- `notes/sessions/YYYY-MM-DD/<task-id>/open_tasks.md`
- `notes/sessions/YYYY-MM-DD/<task-id>/handoff.md`
- `notes/sessions/YYYY-MM-DD/<task-id>/meta.yaml`

Execution policy for this consistency unit:

- During implementation, agent MAY update only session-local files under `notes/sessions/...`.
- Before handoff completion (and before strict validation), agent MUST synchronize `notes/context/*` with the active session in one final pass.

## 5.2 Session Boot Sequence (Read First)

1. Read the 3 context index files under `notes/context/`.
2. Follow active session pointer.
3. Read active session `project_state/open_tasks/handoff/meta`.
4. Read SOP fast-load pack:
   - `docs/SOP/SYSTEM_OVERVIEW.md`
   - `docs/SOP/L0_DATA_FEED.md`
   - `docs/SOP/L1_LOCAL_COMPUTATION.md`
   - `docs/SOP/L2_DECISION_ANALYSIS.md`
   - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
   - `docs/SOP/L4_FRONTEND.md`
5. Run reality check (`git status`, branch, key files).

## 5.3 Session Creation Rule

- One substantive change set = one dedicated session folder.
- Use `scripts/new_session.ps1` (default: create session without updating `notes/context/*` pointers).
- If immediate pointer switch is needed, call `scripts/new_session.ps1 -UpdatePointer`.
- Completed session folders are immutable; never repurpose old session history.

---
## 6. Development Workflow (Execution Order)

1. Explore (`/opsx-explore`): identify constraints and failure modes.
2. Propose (`/opsx-propose`): architecture + contract + verification plan.
3. Apply (`/opsx-apply`): implement with boundary discipline.
4. Verify: pipeline and targeted regressions.
5. Archive (`/opsx-archive`): only after strict validation passes.

Context pointer sync is a handoff-gate action, not a mandatory per-step mutation during implementation.

### 6.1 Test Entry and Cache Isolation

- All pytest MUST run via: `scripts/test/run_pytest.ps1`
- Non-admin context only.
- Cache directory MUST be `tmp/pytest_cache`.

---
## 7. Hard Hooks — Completion Gate (No Verbal Completion)

This section is a machine gate. Agent completion claim without these hooks is invalid.

<MANDATORY_HOOK id="strict-validate-before-handoff">
  <rule>Before declaring handoff complete, agent MUST execute: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`.</rule>
  <rule>Agent MUST provide terminal output summary of that exact command in handoff response.</rule>
</MANDATORY_HOOK>

<MANDATORY_HOOK id="auto-debug-loop-on-failure">
  <rule>If strict validation fails, agent MUST enter automatic debug loop and MUST NOT end session.</rule>
  <loop>
    1) Parse first failing gate.
    2) Fix root cause (not symptom).
    3) Re-run strict validation.
    4) Repeat until pass.
  </loop>
  <rule>Agent is forbidden to exit with "done" while strict gate is red.</rule>
</MANDATORY_HOOK>

<ANTI_PATTERN id="forbidden-handoff-patterns" action="BLOCK_COMPLETION">
  <pattern>"Done" without strict validation command execution evidence</pattern>
  <pattern>Manual claim "should pass" without terminal output</pattern>
  <pattern>Ignoring debt metric mismatch or missing context files</pattern>
</ANTI_PATTERN>

<MANDATORY_HOOK id="quality-gate-before-merge">
  <rule>Before merge/handoff, strict validation MUST include a machine quality gate on changed Python/Rust runtime files.</rule>
  <rule>Quality gate thresholds MUST include all: max nesting depth, max cyclomatic complexity, max function length, max class length, magic number governance ratio, duplicate window count, and max file length.</rule>
  <rule>Max file length threshold is mandatory for both Python (`*.py`) and Rust (`*.rs`) source files: 400 lines.</rule>
  <rule>Quality gate implementation source of truth: `scripts/policy/check_quality_gates.py` + `scripts/policy/quality_thresholds.json`.</rule>
  <rule>If quality gate fails, agent MUST NOT claim completion.</rule>
</MANDATORY_HOOK>

<MANDATORY_HOOK id="openspec-chain-gate-before-runtime-change">
  <rule>Runtime code change in `l0_ingest/`, `l1_compute/`, `l2_decision/`, `l3_assembly/`, `l4_ui/`, `app/`, or `shared/` MUST be linked to OpenSpec change records in `openspec/changes/*` unless `OPENSPEC-EXEMPT` is explicitly declared in handoff.</rule>
  <rule>OpenSpec parent/child governance gate implementation source of truth: `scripts/policy/check_openspec_chain.py`.</rule>
  <rule>Refactor governance proposals MUST satisfy naming, structure, and header template checks.</rule>
</MANDATORY_HOOK>

---
## 8. SOP Sync Contract (Mandatory)

When runtime/contract behavior changes in `l0_ingest/`, `l1_compute/`, `l2_decision/`, `l3_assembly/`, `l4_ui/`, or `app/`:

- At least one relevant `docs/SOP/*.md` file MUST be updated in same change set.
- `handoff.md` MUST list updated SOP files.
- If non-behavioral only, `handoff.md` MUST include `SOP-EXEMPT: <reason>`.

---
## 9. Technical Debt Zero-Tolerance

Unchecked items are active delivery risk by default.

If any unchecked task remains, `handoff.md` MUST include all:

- `DEBT-EXEMPT: <reason>`
- `DEBT-OWNER: <owner>`
- `DEBT-DUE: YYYY-MM-DD`
- `DEBT-RISK: <risk>`

Mandatory metrics in every handoff:

- `DEBT-NEW: <int>`
- `DEBT-CLOSED: <int>`
- `DEBT-DELTA: <int>` where `DEBT-DELTA = DEBT-NEW - DEBT-CLOSED`
- if `DEBT-DELTA > 0`: `DEBT-JUSTIFICATION: <reason>` is mandatory

SLA:

- P0 due today
- P1 within 2 calendar days
- P2 within 5 calendar days

---
## 10. Incident Addendum — ATM Decay Anchor Integrity

- Opening anchor MUST wait for spot stability gate and source-consistency gate.
- Restored anchor MUST pass strict distance validation.
- If spot unavailable at startup, strict mode MUST skip persisted anchor.
- Forensic logs are mandatory for discard paths.
- Maintain separation: `tracker` (orchestration), `anchor` (pure logic), `storage` (persistence), `models/helpers`.

---
## 11. Scripted Enforcement Summary

- Bootstrap: `scripts/new_session.ps1`
- Live broker-dependent backend startup MUST run on the real host environment (outside sandbox); sandbox-local backend launches are invalid evidence for broker/runtime health.
- Startup order MUST be: `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`; only if the real-host strict launch fails on broker connectivity may agent retry `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -Degraded`.
- Validation: `scripts/validate_session.ps1 -Strict`
- Architecture policy: `scripts/policy/layer_boundary_rules.json`
- Quality thresholds: `scripts/policy/quality_thresholds.json`
- Quality gate: `scripts/policy/check_quality_gates.py`
- OpenSpec chain gate: `scripts/policy/check_openspec_chain.py`
- Pytest entry: `scripts/test/run_pytest.ps1`
- CI required check: `.github/workflows/session-validation.yml` (`validate-session` job)
- Remote repo rule (ACTIVE): `refs/heads/master` MUST go through Pull Request; direct push is blocked; required status check `validate-session` MUST pass before merge.

If any scripted gate fails, delivery is not complete.

---
## 12. Rust/Python Cutover Protocol (Binding Execution Contract)

This section defines the **only permitted pattern** for retiring Python module groups in favor of
Rust-backed `.pyd` owners. Any deviation is a P0 process failure.

### 13.1 The Three-Step Pattern (Only Valid Pattern)

```
Step 1 — IMPLEMENT Rust owner
  • Write Rust implementation in the appropriate crate (shared_rust_*/src/ or l0_ingest/l0_rust/src/).
  • Expose the symbol through the crate's lib.rs and rebuild the .pyd.
  • Do NOT create any new Python wrapper file at this step.
  • If an existing neutral Python surface (e.g., facade.py, shared/services/active_options_*.py)
    already re-exports the symbol, update it to point to the Rust .pyd import instead.

Step 2 — RETARGET consumers (if not already done in Step 1)
  • Switch all consumer import sites to the Rust .pyd or the updated neutral surface.
  • Run the full test suite for each affected layer.
  • All parity gates MUST pass before proceeding.

Step 3 — DELETE legacy Python owner (same session as Steps 1+2)
  • Delete every Python runtime file whose logic has been moved to Rust.
  • Delete co-located _native_*.py shim files in the same step.
  • Run the full test suite again.
  • DEBT-DELTA for this session MUST be ≤ 0.
```

Steps 1, 2, and 3 MUST be completed in a **single session** unless a concrete blocking dependency
(named external system, unbuilt dependency crate, dual-run compare requirement) prevents it.
The blocking dependency MUST be declared in `handoff.md` with owner and due date.

### 13.2 Pure Shim Prohibition

A Python file is a **pure shim** if its body contains only:
- `from X import Y` / `from X import (Y, Z, ...)` statements, AND
- `__all__ = [...]` declarations,
- with no function definitions, class definitions, or logic of any kind.

Pure shims MUST NOT be created as migration artifacts.

**Permitted exception**: a neutral surface file that is being *updated in the same session* to
replace re-export statements with direct Rust `.pyd` imports is not a pure shim — it is a live
migration step. It must be updated, not left pointing to the legacy Python owner.

### 13.3 Existing Neutral Surface Rule

Before creating any new Python file during a migration:

1. Check if an existing module in `shared/services/`, `shared/`, or a layer-local module
   already re-exports the target symbol.
2. If yes: update that module to point to the new Rust `.pyd` owner. Do not create a parallel file.
3. If no: create at most **one** neutral surface file per logical group (runtime service,
   engine set, input adapter, etc.) — not one file per class.

### 13.4 Session Atomicity Rules

<MANDATORY_ARCH id="cutover-session-atomicity">
  <rule>Steps 1 (Rust impl), 2 (consumer retarget), and 3 (Python deletion) of the Three-Step Pattern MUST execute in the same session unless a named blocking dependency is declared.</rule>
  <rule>A session that adds new Python wrapper files WITHOUT deleting the legacy Python owner in the same session MUST declare DEBT-DELTA > 0 with a named successor session ID and a due date no later than P1 SLA (2 calendar days).</rule>
  <rule>If a session's P0 task is "cut consumer imports to a neutral surface", then P1 (Rust owner replacement) MUST be scoped to the same session or the immediately following session — not deferred to a vague future wave.</rule>
  <rule>A session MUST NOT end with DEBT-DELTA > 0 caused purely by temporary wrapper files if those files have no logic and could have been avoided by updating an existing surface instead.</rule>
</MANDATORY_ARCH>

### 13.5 Sub-Wave Atomicity (for large module groups like l0_runtime)

When a module group is too large for one session:

- Each sub-wave targets a named responsibility cluster (e.g., `normalize/pipeline`, `state/`).
- Each sub-wave MUST delete the Python files it migrates **in the same sub-wave session**.
- `facade.py` (or equivalent top-level entry) acts as the blast-radius limiter and is deleted last.
- Sub-waves MUST NOT add new Python wrapper files at the `shared/services/` root level.
- The existing `facade.py` IS the neutral surface — route through it, do not duplicate it.

### 13.6 Anti-Patterns (Hard Stop)

<ANTI_PATTERN id="cutover-anti-patterns" action="ABORT_AND_ROLLBACK_PLAN">
  <pattern>New Python file created during migration whose body is entirely re-export statements (pure shim)</pattern>
  <pattern>Consumer import sites switched to a neutral surface in session N, Rust owner not implemented until session N+2 or later</pattern>
  <pattern>Sub-wave that migrates logic to Rust but does not delete the Python source file in the same session (without a declared dual-run or blocking dependency)</pattern>
  <pattern>Multiple root-level wrapper files created (e.g., active_options_runtime.py, active_options_engines.py, active_options_input.py) when a single updated neutral surface could serve all consumers</pattern>
  <pattern>DEBT-DELTA > 0 in a migration session caused by temporary wrapper files that own no logic</pattern>
  <required_reaction>
    1) STOP current migration plan immediately.
    2) REVERT any pure-shim files added this session.
    3) REDESIGN: identify the single existing neutral surface that can absorb the migration.
    4) Re-execute the Three-Step Pattern (§13.1) in one session.
  </required_reaction>
</ANTI_PATTERN>

---
## 12. Final Operating Principle

Agent behavior standard:

- No shortest-path hacks.
- No boundary erosion for speed.
- No hidden failures.
- No undocumented handoff.

Trade like an institution. Build like a deterministic system.

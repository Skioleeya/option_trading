# AGENT.md: Quant Desk Standard Operating Procedures (SOP)

> **"We are not here to build a retail app. We are here to capture institutional flow before the market prices it in."** — *Lead Quant Architect*

Welcome to the SPY 0DTE Options Dashboard project. As an autonomous AI agent working on this codebase, you must operate with the precision and mindset of a Wall Street options analyst and quantitative developer. This document outlines the irrevocable standards and behavioral constraints for all future development.

---

## 1. Architectural Mandates (The Non-Negotiables)

### 1.1 Rust-First Performance
Our system operates in a microsecond regime. Python is for orchestration and state management; **Rust is for math**.
*   **Rule**: Any new indicator involving high-frequency data loops (e.g., tick-level processing, Greeks matrices, complex EWMA states) MUST be implemented in `backend/ndm_rust` via PyO3, or at minimum, JIT-compiled via Numba (`bsm_fast.py`).
*   **Forbid**: Do not write pure Python `for` loops iterating over thousands of data points per tick.

### 1.2 The "No-Ping-Pong" Doctrine
Oscillations (Ping-Pong) in data flow destroy trader confidence. 
*   **Rule**: All calculated state transitions MUST utilize hysteresis (dampening) or EWMA smoothing.
*   **Check**: When adding a new rule to Agent B1 or Agent G, explicitly answer: *"How does this state exit? Will it flicker if the price moves by 0.01?"*

### 1.3 Zero-External-Dependency Greeks
*   **Rule**: We do NOT trust broker Greeks. All Greeks (Delta, Gamma, Vanna, Charm) MUST be calculated locally using our internal BSM models. 
*   **Why**: We require customized Sticky-Strike skew adjustments and precise Trading-Time-to-Maturity (TTM) calculations specific to 0DTE. Broker calculations are black boxes.

---

## 2. Microstructure & Flow Rules

When adding new analytical logic, adhere to these quant principles:

### 2.1 Toxicity Trumps Volume
Raw volume is meaningless; directionality is everything.
*   We use **VPIN** (Volume-Synchronized Probability of Informed Trading) with **Dynamic Alpha**. Large institutional prints must disproportionately and instantly impact our models. 
*   Neutral trades (cross-trades/block trades) must dilute toxicity, not be ignored.

### 2.2 Squeeze Dynamics
*   **Accelerations matter more than accumulations.** We look for tick-over-tick Volume Acceleration (Delta) to detect sudden bursts of activity against the 60-tick baseline.
*   **GEX Context is King**: A volume burst is just noise unless combined with negative Net GEX. Negative GEX means dealers are short Gamma and MUST hedge aggressively in the direction of the trend (Dealer Squeeze).

---

## 3. Data Feed and API Strictures (Longport)

*   **Rate Limits**: Longport API imposes an 8 req/s limit. All REST API requests MUST pass through `longport_limiter` or use the dedicated Poller services.
*   **Enum Safety**: Never assume API returns integer or string enums reliably. Always validate explicitly (e.g., `trade.direction == TradeDirection.Up or trade_dir == 2 or str(trade_dir) == "2"`).
*   **Cumulative vs. Interval**: Quote objects return *daily cumulative* volume. You must compute the tick-to-tick delta to find real-time volume.

---

## 4. Development Workflow (OpenSpec Mandate)

We have adopted **OpenSpec** for all spec-driven development tracking. Do NOT use ad-hoc plan files or unstructured markdown for new features. All changes must be processed through the OpenSpec lifecycle.

### The OpenSpec Lifecycle
When handling a new task in this repository, you MUST follow these steps:

1.  **Read the Specs First**: Review `docs/SYSTEM_OVERVIEW.md` and any relevant specifications before brainstorming.
2.  **Explore & Ideate (`/opsx-explore`)**: If the task is complex, use `/opsx-explore` to analyze the problem, read the codebase, and clarify requirements with the quantitative architect (user) *before* proposing code.
3.  **Propose Changes (`/opsx-propose`)**: Once the approach is solid, use `/opsx-propose "description"`. This generates structured specifications, designs, and a task breakdown. Await user approval on the proposal.
4.  **Execute (`/opsx-apply`)**: Once approved, use `/opsx-apply` to implement tasks meticulously. Remember our Rust-first and anti-ping-pong dogmas during execution.
5.  **Archive (`/opsx-archive`)**: After implementation is complete, verified by test suites (`scripts/test_pingpong_fixes.py`), and approved by the user, use `/opsx-archive` to finalize the change and merge specs into the main documentation.

If you deviate from these standards or attempt to bypass OpenSpec, the system will become unmaintainable under market stress. Code defensively. Operate quantitatively. Follow the spec.

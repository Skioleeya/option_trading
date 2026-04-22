## Purpose

Define how `l1_compute/analysis/greeks_engine.py` may retain or remove NumPy allocation after
Rust and GPU ownership has moved below the Python orchestration layer.

## Requirements

### Requirement: Classify Each NumPy Allocation By Owner Need

Each surviving NumPy allocation in `greeks_engine.py` MUST be mapped to the direct downstream
owner that requires it.

#### Scenario: Allocation Is Bridge-Only

WHEN a `numpy` allocation is used only to marshal inputs into an owner that accepts Python
sequences directly
THEN that allocation MUST be removed.

### Requirement: Python Runtime Compute Owners Cannot Satisfy This Proposal By Documentation Alone

If a NumPy allocation feeds a Python runtime compute owner, this proposal MUST remain blocked on
the real owner migration instead of treating the current path as acceptable bridge retention.

#### Scenario: Allocation Feeds `bsm_fast.compute_greeks_batch`

WHEN a `greeks_engine.py` allocation feeds `bsm_fast.compute_greeks_batch()` or another Python
runtime compute owner
THEN the allocation MUST NOT be marked resolved solely by a justification comment
AND the proposal MUST link the concrete owner-migration change before it can close.

### Requirement: Retained NumPy Must Have An Explicit Owner Justification

Retained NumPy usage MUST describe the owner-boundary requirement that makes the allocation
necessary.

#### Scenario: Downstream Owner Requires Dense Array Input

WHEN the downstream Rust or GPU owner requires a dense array input type
THEN `greeks_engine.py` MAY retain the NumPy allocation
AND it MUST document that the allocation exists for owner-boundary compatibility rather than
Python-side compute.

### Requirement: No Semantic Drift

The audit MUST preserve existing Greeks batch semantics.

#### Scenario: Audit Session Edits Allocation Code

WHEN `greeks_engine.py` is modified under this proposal
THEN the file MUST keep the same downstream compute ownership
AND it MUST NOT introduce new numerical formulas or fallback loops in Python.

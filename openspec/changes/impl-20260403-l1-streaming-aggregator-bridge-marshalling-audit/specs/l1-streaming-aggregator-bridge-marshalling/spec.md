## Purpose

Define the allowed Python-to-Rust marshalling pattern for `l1_compute/aggregation/streaming_aggregator.py`
without permitting residual Python wall / flip compute to be treated as complete cleanup.

## Requirements

### Requirement: Prefer Native Python Sequences At The Bridge

The `streaming_aggregator.py` bridge MUST pass native Python sequences directly into the Rust
owner when the PyO3 function signatures accept them without behavior change.

#### Scenario: Direct Sequence Pass-Through Works

WHEN the Rust aggregation functions accept Python `list` or `tuple` inputs directly
THEN `streaming_aggregator.py` MUST remove the redundant `numpy` import and `np.asarray(...)`
bridge calls.

#### Scenario: Rust Wall Owner Accepts Native Sequences

WHEN the wall-selection owner accepts Python sequences directly
THEN `streaming_aggregator.py` MUST pass native `list[float]` values to Rust
AND it MUST NOT rebuild NumPy arrays just to satisfy that boundary.

### Requirement: Any Retained NumPy Use Must Be Bridge-Only And Explicit

If NumPy remains in `streaming_aggregator.py`, it MUST be limited to marshalling into the Rust
owner and MUST NOT add Python-side arithmetic or fallback compute.

#### Scenario: NumPy Retention Is Still Necessary

WHEN the Rust bridge rejects direct Python sequence inputs
THEN the file MAY retain a minimal NumPy conversion path
AND it MUST include an explicit inline justification that the import exists only for PyO3
bridge marshalling.

### Requirement: Residual Python Wall And Flip Compute Must Not Be Hidden By Bridge Cleanup

The proposal MUST NOT be considered complete while `_recompute_walls()` or `_find_flip_level()`
remain live Python numerical owners without an explicit retirement path.

#### Scenario: Bridge Audit Finishes Before Wall / Flip Retirement

WHEN bridge-only NumPy cleanup is complete but `_recompute_walls()` or `_find_flip_level()`
still own runtime numerical logic in Python
THEN this proposal MUST remain open
AND it MUST link the concrete successor change that retires those Python owners.

### Requirement: Flip Level Must Be Owned By Rust

The cumulative flip interpolation for streaming aggregation MUST be computed in Rust and
returned in the aggregate payload as `flip_level_cumulative` with compatibility alias `flip_level`.

#### Scenario: Flip-Level Is Rehomed

WHEN `aggregate_greeks_full` returns `flip_level_cumulative`
THEN `streaming_aggregator.py` MUST take that value directly from the Rust payload
AND it MUST NOT keep a Python `_find_flip_level()` owner.

### Requirement: No Python Compute Regression

The marshalling audit MUST NOT reopen Python compute ownership in the file.

#### Scenario: Cleanup Session Touches The Bridge

WHEN `streaming_aggregator.py` is edited under this proposal
THEN the file MUST move toward a Rust delegation surface
AND it MUST NOT add new numerical loops, statistical formulas, or Python fallback aggregation.

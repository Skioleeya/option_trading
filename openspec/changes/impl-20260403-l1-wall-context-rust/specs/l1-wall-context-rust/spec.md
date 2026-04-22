## Purpose

Move the numerical logic in `l1_compute/microstructure/wall_context_builder.py` into the Rust
microstructure ownership cluster while keeping the existing L1 contract stable.

## Requirements

### Requirement: Wall Context Numerical Compute Must Be Rust-Owned

`wall_context_builder.py` MUST delegate its numerical wall-context computation to the Rust
microstructure owner once the owner is importable.

#### Scenario: Rust Wall-Context Helper Is Importable

WHEN the Rust wall-context helper is exposed through `shared_rust.services`
THEN `wall_context_builder.py` MUST call that helper
AND it MUST NOT retain runtime NumPy numerical compute.

### Requirement: Existing L1 Contract Must Stay Stable

The cutover MUST preserve the existing wall-context semantics consumed by downstream layers.

#### Scenario: Downstream Consumer Reads Wall Context

WHEN downstream L1 or L2 code reads wall-context output after the cutover
THEN the field semantics MUST remain unchanged
AND no new cross-layer dependency may be introduced.

### Requirement: RecordBatch Hot Path Must Preserve Arrow-First Semantics

The `RecordBatch` branch of `estimate_near_wall_liquidity()` MUST preserve the Arrow-first hot
path during the Rust cutover.

#### Scenario: Wall Context Is Built From A RecordBatch

WHEN `wall_context_builder.py` receives `pa.RecordBatch` input
THEN the cutover MUST avoid Python-side list or NumPy materialization before entering Rust
AND it MUST preserve parity with the prior `RecordBatch` semantics.

### Requirement: Migration Surface Must Stay Minimal

The cutover MUST use the existing Rust ownership cluster unless a file-length split is required.

#### Scenario: `microstructure.rs` Approaches The File-Length Ceiling

WHEN adding the wall-context helper would make `microstructure.rs` exceed the repository file
limit
THEN the Rust ownership MAY be split by responsibility inside the same cluster
AND the session MUST NOT create a new pure Python shim to carry the migration.

### Requirement: Delegation Layer Must Reject Invalid Rust Return Values

The Python delegation layer MUST fail explicitly when the Rust wall-context owner returns invalid
runtime values.

#### Scenario: Invalid Gamma Regime

WHEN the Rust owner returns a `gamma_regime` outside `SHORT_GAMMA|LONG_GAMMA|NEUTRAL`
THEN `wall_context_builder.py` MUST raise an explicit runtime error
AND it MUST NOT silently coerce or pass through the invalid regime.

#### Scenario: Invalid Near-Wall Liquidity

WHEN the Rust owner returns `near_wall_liquidity` that is non-finite or `< 1.0`
THEN `wall_context_builder.py` MUST raise an explicit runtime error
AND it MUST NOT silently clamp or normalize the invalid value in Python.

#### Scenario: Invalid Wall-Context Metrics

WHEN the Rust owner returns non-finite numeric wall-context metrics
THEN `wall_context_builder.py` MUST raise an explicit runtime error
AND it MUST NOT silently continue with a partially invalid payload.

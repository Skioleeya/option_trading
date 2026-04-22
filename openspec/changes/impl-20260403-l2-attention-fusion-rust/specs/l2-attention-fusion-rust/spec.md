## Purpose

Move the numerical core of `l2_decision/fusion/attention_fusion.py` into Rust without changing
the L2 decision contract.

## Requirements

### Requirement: Attention Fusion Compute Must Be Rust-Owned

`attention_fusion.py` MUST delegate its numerical fusion compute to a Rust owner once the owner
is importable.

#### Scenario: Rust Owner Is Importable

WHEN `shared_rust.services.compute_attention_fused` is importable
THEN `attention_fusion.py` MUST call the Rust owner
AND it MUST NOT retain NumPy softmax or dot-product compute on the runtime path.

### Requirement: Attention Weights Must Remain Part Of The Rust Contract

The Rust owner MUST return the normalized attention weights needed to populate
`FusedDecision.fusion_weights`.

#### Scenario: Attention Mode Produces A Decision

WHEN `AttentionFusionEngine` fuses active signals in attention mode
THEN the Rust owner MUST return the normalized weights in active-signal order
AND Python MUST map those weights back into `fusion_weights` without recomputing softmax locally.

### Requirement: Numerical Stability Must Match The Prior Softmax Semantics

The Rust implementation MUST preserve the stabilized softmax behavior used by the Python owner.

#### Scenario: Large Positive Or Negative Logits Arrive

WHEN `compute_attention_fused` receives logits with large magnitude differences
THEN it MUST apply a numerically stable softmax
AND it MUST produce the same fused score and confidence as the prior Python implementation
within the approved parity tolerance.

### Requirement: L2 Contract Must Stay Stable

The cutover MUST keep the existing L2-facing output semantics unchanged.

#### Scenario: Existing L2 Consumer Calls Attention Fusion

WHEN downstream L2 code consumes the fusion result after the Rust cutover
THEN the returned score, confidence, and `fusion_weights` semantics MUST remain unchanged
AND no new L3/L4-facing contract dependency may be introduced.

### Requirement: Delegation Layer Must Reject Invalid Rust Return Values

The Python delegation layer MUST fail explicitly when the Rust owner returns invalid runtime values.

#### Scenario: Non-finite Score Or Confidence

WHEN `compute_attention_fused` returns `raw_score` or `confidence` that is non-finite
THEN `AttentionFusionEngine` MUST raise an explicit runtime error
AND it MUST NOT continue with silent fallback or silent clamping.

#### Scenario: Invalid Weights

WHEN `compute_attention_fused` returns attention weights that are non-finite, negative,
or not normalized within tolerance
THEN `AttentionFusionEngine` MUST raise an explicit runtime error
AND it MUST NOT silently renormalize those invalid weights in Python.

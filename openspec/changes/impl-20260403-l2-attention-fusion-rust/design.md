## Context

`attention_fusion.py` currently computes a stabilized softmax over logits and then performs a
weighted sum over signal values. The file is small but hot. It is the only clearly identified L2
runtime source in the cleanup list that still owns real NumPy math.

## Goal

Move the numerical core into Rust while leaving Python responsible only for orchestration,
input shaping, and contract mapping.

## Non-Goals

- No changes to the surrounding L2 fusion pipeline
- No new L3/L4-facing contract fields
- No persistent Python fallback branch

## Proposed Rust Surface

```rust
#[pyfunction]
pub fn compute_attention_fused(
    signal_values: Vec<f64>,
    logits: Vec<f64>,
    regime_key: &str,
) -> PyResult<AttentionFusionResult>
```

Where `AttentionFusionResult` carries:

- `raw_score: f64`
- `confidence: f64`
- `fusion_weights: Vec<f64>` in the same active-signal order used by Python

The Rust function owns:

- max-shifted softmax for numerical stability
- weighted sum of signal values
- calibrated confidence output
- the normalized attention weights needed to populate `FusedDecision.fusion_weights`

Python remains responsible for:

- regime lookup / config wiring
- calling the Rust owner
- mapping returned weights back onto `active_names`
- packaging the full result into the existing L2 contract

## Cross-Proposal Dependency

This cutover should follow the two marshalling-audit proposals so the Python wrapper can adopt
the established boundary pattern instead of inventing another transient array convention.

## Success Signal

`attention_fusion.py` becomes a thin Rust delegation file with no runtime NumPy arithmetic, while
still populating the same `fusion_weights` consumed by `DecisionOutput` and `DecisionAuditEntry`.

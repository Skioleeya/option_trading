use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;

fn sanitize(value: f64) -> f64 {
    if value.is_finite() {
        value
    } else {
        0.0
    }
}

fn sigmoid(value: f64) -> f64 {
    if value >= 0.0 {
        let exp_neg = (-value).exp();
        1.0 / (1.0 + exp_neg)
    } else {
        let exp_pos = value.exp();
        exp_pos / (1.0 + exp_pos)
    }
}

#[pyfunction]
#[pyo3(signature = (signal_values, logits, regime_key, platt_a=1.0, platt_b=0.0))]
fn compute_attention_fused(
    signal_values: Vec<f64>,
    logits: Vec<f64>,
    regime_key: &str,
    platt_a: f64,
    platt_b: f64,
) -> PyResult<(f64, f64, Vec<f64>)> {
    if signal_values.len() != logits.len() {
        return Err(PyValueError::new_err(
            "compute_attention_fused requires equal-length signal_values and logits",
        ));
    }
    if signal_values.is_empty() {
        return Err(PyValueError::new_err(
            "compute_attention_fused requires non-empty inputs",
        ));
    }

    let _ = regime_key;

    let mut max_logit = f64::NEG_INFINITY;
    for &logit in &logits {
        let value = sanitize(logit);
        if value > max_logit {
            max_logit = value;
        }
    }
    if !max_logit.is_finite() {
        max_logit = 0.0;
    }

    let mut exp_values = Vec::with_capacity(logits.len());
    let mut exp_sum = 0.0;
    for &logit in &logits {
        let shifted = sanitize(logit) - max_logit;
        let value = shifted.exp();
        exp_values.push(value);
        exp_sum += value;
    }

    let mut weights = Vec::with_capacity(exp_values.len());
    if !exp_sum.is_finite() || exp_sum <= 0.0 {
        let uniform = 1.0 / exp_values.len() as f64;
        for _ in 0..exp_values.len() {
            weights.push(uniform);
        }
    } else {
        for value in exp_values {
            weights.push(value / exp_sum);
        }
    }

    let mut raw_score = 0.0;
    for idx in 0..weights.len() {
        raw_score += weights[idx] * sanitize(signal_values[idx]);
    }
    raw_score = raw_score.clamp(-1.0, 1.0);

    let calibrated = sanitize(platt_a) * raw_score + sanitize(platt_b);
    let confidence = sigmoid(calibrated).clamp(0.0, 1.0);

    Ok((raw_score, confidence, weights))
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(compute_attention_fused, module)?)?;
    Ok(())
}

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;

fn sanitize_nonnegative(value: f64) -> f64 {
    if value.is_finite() && value > 0.0 {
        value
    } else {
        0.0
    }
}

fn clamp_unit(value: f64) -> f64 {
    if !value.is_finite() {
        0.0
    } else {
        value.clamp(0.0, 1.0)
    }
}

fn entropy_from_weights(weights: &[f64]) -> f64 {
    let total: f64 = weights.iter().copied().sum();
    if total <= 0.0 {
        return 0.0;
    }

    let mut entropy = 0.0;
    for &weight in weights {
        if weight > 0.0 {
            let p = weight / total;
            entropy -= p * p.ln();
        }
    }
    entropy
}

#[pyfunction]
#[pyo3(signature = (buy_vols, sell_vols, threshold_elevated, threshold_toxic))]
fn compute_vpin_regime(
    buy_vols: Vec<f64>,
    sell_vols: Vec<f64>,
    threshold_elevated: f64,
    threshold_toxic: f64,
) -> PyResult<u8> {
    let len = buy_vols.len();
    if sell_vols.len() != len {
        return Err(PyValueError::new_err(
            "compute_vpin_regime requires equal-length buy_vols and sell_vols",
        ));
    }

    if len == 0 {
        return Ok(0);
    }

    let mut total_score = 0.0;
    let mut bucket_count = 0usize;
    for idx in 0..len {
        let buy_v = sanitize_nonnegative(buy_vols[idx]);
        let sell_v = sanitize_nonnegative(sell_vols[idx]);
        let total = buy_v + sell_v;
        let score = if total > 0.0 {
            (buy_v - sell_v).abs() / total
        } else {
            0.0
        };
        total_score += score;
        bucket_count += 1;
    }

    let avg_score = total_score / bucket_count as f64;
    if avg_score >= threshold_toxic {
        Ok(2)
    } else if avg_score >= threshold_elevated {
        Ok(1)
    } else {
        Ok(0)
    }
}

#[pyfunction]
#[pyo3(signature = (price_buckets, ema_prev, alpha))]
fn compute_vol_accel_entropy(
    price_buckets: Vec<f64>,
    ema_prev: f64,
    alpha: f64,
) -> PyResult<(f64, f64)> {
    let mut weights = Vec::with_capacity(price_buckets.len());
    let mut tick_volume = 0.0;

    for value in price_buckets {
        let vol = sanitize_nonnegative(value);
        tick_volume += vol;
        weights.push(vol);
    }

    let entropy = entropy_from_weights(&weights);
    let alpha = clamp_unit(alpha);
    let ema_next = if !ema_prev.is_finite() || ema_prev <= 0.0 {
        tick_volume
    } else {
        ema_prev + alpha * (tick_volume - ema_prev)
    };

    Ok((entropy, ema_next))
}

#[pyfunction]
#[pyo3(signature = (features, min_entropy))]
fn compute_entropy_gate(
    features: Vec<f64>,
    min_entropy: f64,
) -> PyResult<bool> {
    let mut weights = Vec::with_capacity(features.len());
    for value in features {
        weights.push(sanitize_nonnegative(value));
    }

    Ok(entropy_from_weights(&weights) >= min_entropy)
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(compute_vpin_regime, module)?)?;
    module.add_function(wrap_pyfunction!(compute_vol_accel_entropy, module)?)?;
    module.add_function(wrap_pyfunction!(compute_entropy_gate, module)?)?;
    Ok(())
}

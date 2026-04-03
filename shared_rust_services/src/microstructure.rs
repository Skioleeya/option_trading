use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyModule};

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

fn extract_f64_sequence(values: &Bound<'_, PyAny>) -> PyResult<Vec<f64>> {
    if let Ok(vec_values) = values.extract::<Vec<f64>>() {
        return Ok(vec_values);
    }

    if values.hasattr("to_numpy")? {
        if let Ok(np_values) = values.call_method1("to_numpy", (false,)) {
            if let Ok(vec_values) = np_values.extract::<Vec<f64>>() {
                return Ok(vec_values);
            }
        }
        let np_values = values.call_method0("to_numpy")?;
        if let Ok(vec_values) = np_values.extract::<Vec<f64>>() {
            return Ok(vec_values);
        }
    }

    Err(PyValueError::new_err(
        "Expected numeric sequence or array-like object compatible with to_numpy()",
    ))
}

fn mapping_field_f64(row: &Bound<'_, PyAny>, key: &str) -> f64 {
    if let Ok(value_obj) = row.call_method1("get", (key, 0.0))
        && let Ok(value) = value_obj.extract::<f64>()
        && value.is_finite()
    {
        return value;
    }
    0.0
}

fn extract_wall_snapshot_inputs(snapshot: &Bound<'_, PyAny>) -> PyResult<(Vec<f64>, Vec<f64>)> {
    if snapshot.hasattr("column")? {
        let strikes_obj = snapshot.call_method1("column", ("strike",))?;
        let volumes_obj = snapshot.call_method1("column", ("volume",))?;
        let strikes = extract_f64_sequence(&strikes_obj)?;
        let volumes = extract_f64_sequence(&volumes_obj)?;
        return Ok((strikes, volumes));
    }

    if let Ok(iter) = snapshot.try_iter() {
        let mut strikes = Vec::new();
        let mut volumes = Vec::new();
        for item in iter {
            let row = item?;
            strikes.push(mapping_field_f64(&row, "strike"));
            volumes.push(mapping_field_f64(&row, "volume"));
        }
        return Ok((strikes, volumes));
    }

    Err(PyValueError::new_err(
        "Expected chain_snapshot as RecordBatch-like object or iterable rows",
    ))
}

fn classify_gamma_regime(net_gex: f64, neutral_abs: f64) -> &'static str {
    let neutral = sanitize_nonnegative(neutral_abs);
    let net = if net_gex.is_finite() { net_gex } else { 0.0 };
    if net.abs() <= neutral {
        "NEUTRAL"
    } else if net < 0.0 {
        "SHORT_GAMMA"
    } else {
        "LONG_GAMMA"
    }
}

fn compute_near_wall_liquidity(
    strikes: &[f64],
    volumes: &[f64],
    call_wall: f64,
    put_wall: f64,
    band: f64,
) -> f64 {
    let mut near_liq = 0.0;
    let mut total_vol = 0.0;
    let bandwidth = if band.is_finite() && band > 0.0 { band } else { 1.0 };
    let call_ref = if call_wall.is_finite() && call_wall > 0.0 {
        call_wall
    } else {
        0.0
    };
    let put_ref = if put_wall.is_finite() && put_wall > 0.0 {
        put_wall
    } else {
        0.0
    };

    for idx in 0..strikes.len() {
        let strike = strikes[idx];
        let volume = sanitize_nonnegative(volumes[idx]);
        total_vol += volume;

        if !strike.is_finite() || strike <= 0.0 {
            continue;
        }
        if call_ref > 0.0 && (strike - call_ref).abs() <= bandwidth {
            near_liq += volume;
            continue;
        }
        if put_ref > 0.0 && (strike - put_ref).abs() <= bandwidth {
            near_liq += volume;
        }
    }

    if near_liq <= 0.0 {
        near_liq = total_vol;
    }
    near_liq.max(1.0)
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

#[pyfunction]
#[pyo3(signature = (net_gex, neutral_abs))]
fn classify_wall_gamma_regime(
    net_gex: f64,
    neutral_abs: f64,
) -> PyResult<String> {
    Ok(classify_gamma_regime(net_gex, neutral_abs).to_string())
}

#[pyfunction]
#[pyo3(signature = (chain_snapshot, call_wall, put_wall, band))]
fn estimate_near_wall_liquidity(
    chain_snapshot: &Bound<'_, PyAny>,
    call_wall: f64,
    put_wall: f64,
    band: f64,
) -> PyResult<f64> {
    let (strikes_v, volumes_v) = extract_wall_snapshot_inputs(chain_snapshot)?;
    if strikes_v.len() != volumes_v.len() {
        return Err(PyValueError::new_err(
            "estimate_near_wall_liquidity requires equal-length strikes and volumes",
        ));
    }

    Ok(compute_near_wall_liquidity(
        &strikes_v,
        &volumes_v,
        call_wall,
        put_wall,
        band,
    ))
}

#[pyfunction]
#[pyo3(signature = (chain_snapshot, net_gex, call_wall, put_wall, call_wall_gex, put_wall_gex, band, neutral_abs, cap_bps))]
fn compute_wall_context_metrics(
    chain_snapshot: &Bound<'_, PyAny>,
    net_gex: f64,
    call_wall: f64,
    put_wall: f64,
    call_wall_gex: f64,
    put_wall_gex: f64,
    band: f64,
    neutral_abs: f64,
    cap_bps: f64,
) -> PyResult<(String, f64, f64, f64, f64)> {
    let (strikes_v, volumes_v) = extract_wall_snapshot_inputs(chain_snapshot)?;
    if strikes_v.len() != volumes_v.len() {
        return Err(PyValueError::new_err(
            "compute_wall_context_metrics requires equal-length strikes and volumes",
        ));
    }

    let regime = classify_gamma_regime(net_gex, neutral_abs).to_string();
    let near_wall_hedge_notional_m =
        sanitize_nonnegative(call_wall_gex.abs()) + sanitize_nonnegative(put_wall_gex.abs());
    let near_wall_liquidity = compute_near_wall_liquidity(
        &strikes_v,
        &volumes_v,
        call_wall,
        put_wall,
        band,
    );
    let hedge_flow_intensity = near_wall_hedge_notional_m / near_wall_liquidity.max(1.0);
    let cap = sanitize_nonnegative(cap_bps);
    let direction = match regime.as_str() {
        "SHORT_GAMMA" => 1.0,
        "LONG_GAMMA" => -0.5,
        _ => 0.0,
    };
    let counterfactual_vol_impact_bps = direction * (hedge_flow_intensity * 100.0).min(cap);

    Ok((
        regime,
        hedge_flow_intensity,
        counterfactual_vol_impact_bps,
        near_wall_hedge_notional_m,
        near_wall_liquidity,
    ))
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(compute_vpin_regime, module)?)?;
    module.add_function(wrap_pyfunction!(compute_vol_accel_entropy, module)?)?;
    module.add_function(wrap_pyfunction!(compute_entropy_gate, module)?)?;
    module.add_function(wrap_pyfunction!(classify_wall_gamma_regime, module)?)?;
    module.add_function(wrap_pyfunction!(estimate_near_wall_liquidity, module)?)?;
    module.add_function(wrap_pyfunction!(compute_wall_context_metrics, module)?)?;
    Ok(())
}

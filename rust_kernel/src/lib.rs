use pyo3::prelude::*;
use numpy::{PyArray1, PyReadonlyArray1};

/// Computes the Pearson correlation coefficient between two slices of f64.
/// 
/// Uses a single-pass O(N) Welford-style algorithm or expanded mathematical formulation.
/// This formulation is extremely fast, avoiding Python loops and sqrt overhead.
#[pyfunction]
fn pearson_r(spots: Vec<f64>, ivs: Vec<f64>) -> PyResult<Option<f64>> {
    let n = spots.len();
    if n < 2 || n != ivs.len() {
        return Ok(None);
    }

    let mut sum_x = 0.0;
    let mut sum_y = 0.0;
    let mut sum_x2 = 0.0;
    let mut sum_y2 = 0.0;
    let mut sum_xy = 0.0;

    for i in 0..n {
        let x = spots[i];
        let y = ivs[i];

        sum_x += x;
        sum_y += y;
        sum_x2 += x * x;
        sum_y2 += y * y;
        sum_xy += x * y;
    }

    let n_f64 = n as f64;
    let numerator = n_f64 * sum_xy - sum_x * sum_y;
    let denominator_x = n_f64 * sum_x2 - sum_x * sum_x;
    let denominator_y = n_f64 * sum_y2 - sum_y * sum_y;

    if denominator_x <= 0.0 || denominator_y <= 0.0 {
        return Ok(None);
    }

    let r = numerator / (denominator_x.sqrt() * denominator_y.sqrt());
    
    // Clamp to [-1.0, 1.0] to handle floating point inaccuracies
    let r_clamped = if r > 1.0 {
        1.0
    } else if r < -1.0 {
        -1.0
    } else {
        r
    };

    Ok(Some(r_clamped))
}

/// Computes Vanna Flow logic natively, detecting instantaneous Vanna Flip.
/// Given a history of (timestamp, correlation), checks if the change > 0.6 within 120 secs.
#[pyfunction]
#[pyo3(signature = (now_mono, current_corr, history))]
fn detect_vanna_flip(now_mono: f64, current_corr: Option<f64>, history: Vec<(f64, f64)>) -> PyResult<bool> {
    if let Some(corr) = current_corr {
        if history.len() < 10 {
            return Ok(false);
        }

        let two_min_ago = now_mono - 120.0;
        let mut past_corr: Option<f64> = None;

        for (ts, hist_corr) in history.iter() {
            if *ts >= two_min_ago {
                past_corr = Some(*hist_corr);
                break;
            }
        }

        if let Some(pc) = past_corr {
            let delta = corr - pc;
            return Ok(delta > 0.6);
        }
    }
    Ok(false)
}

/// Kernel for VPIN calculation. Processes a batch of trades and updates the EMA and bucket states.
/// 
/// Returns: (new_ema_v, new_ema_dv, new_bucket_accum, new_bucket_dv, new_bucket_tv, toxicity_score, vpin_score)
#[pyfunction]
fn update_vpin_logic(
    mut ema_v: f64,
    mut ema_dv: f64,
    mut b_accum: f64,
    mut b_dv: f64,
    mut b_tv: f64,
    bucket_size: f64,
    trades: Vec<(f64, f64)>, // (volume, dir_sign)
) -> PyResult<(f64, f64, f64, f64, f64, f64, f64)> {
    for (vol, dir_sign) in trades {
        if vol <= 0.0 { continue; }

        // 1. Dynamic Alpha EMA (Practice 2)
        let alpha = (vol / bucket_size.max(1.0)).min(1.0);
        ema_v = (1.0 - alpha) * ema_v + alpha * vol;
        ema_dv = (1.0 - alpha) * ema_dv + alpha * (dir_sign * vol);

        // 2. Bucket Integration
        b_accum += vol;
        b_dv += dir_sign * vol;
        b_tv += vol;

        if b_accum >= bucket_size {
            // Bucket full - reset but keep remainder for smoothness if any
            // (Simple reset for now to match current Python implementation)
            b_accum = 0.0;
            b_dv = 0.0;
            b_tv = 0.0;
        }
    }

    let toxicity = if ema_v > 1e-8 { ema_dv / ema_v } else { 0.0 };
    let vpin = if b_tv > 1e-8 { b_dv / b_tv } else { 0.0 };

    Ok((ema_v, ema_dv, b_accum, b_dv, b_tv, toxicity, vpin))
}

/// Kernel for Volume Acceleration Ratio. 
/// 
/// Returns: (new_ema, ratio) using decoupled previous EMA as baseline.
#[pyfunction]
fn compute_vol_accel(
    tick_volume: f64,
    current_ema: f64,
    alpha: f64,
) -> PyResult<(f64, f64)> {
    let ratio = if current_ema > 0.0 {
        tick_volume / current_ema.max(1.0)
    } else {
        1.0
    };

    let new_ema = if current_ema == 0.0 {
        tick_volume
    } else {
        alpha * tick_volume + (1.0 - alpha) * current_ema
    };

    Ok((new_ema, ratio))
}

/// Phase 2: Zero-Copy Bridge Test
/// Accepts contiguous Python float32 (NumPy) arrays directly as C-layout memory.
#[pyfunction]
#[pyo3(signature = (spots, strikes, ivs, is_call))]
fn compute_from_arrays<'py>(
    _py: Python<'py>,
    spots: PyReadonlyArray1<'py, f32>,
    strikes: PyReadonlyArray1<'py, f32>,
    ivs: PyReadonlyArray1<'py, f32>,
    is_call: PyReadonlyArray1<'py, bool>, // Numpy uses 1 byte per bool
) -> PyResult<u32> {
    // 1. Borrow raw C-contiguous memory slices without copying
    // Safety: we must guarantee that the Python GC does not move or drop the underlying NumPy array.
    // PyReadonlyArray1 already enforces this via the PyO3 GIL lock.
    let spots_slice = unsafe { spots.as_slice().unwrap() };
    let strikes_slice = unsafe { strikes.as_slice().unwrap() };
    let ivs_slice = unsafe { ivs.as_slice().unwrap() };
    let is_call_slice = unsafe { is_call.as_slice().unwrap() };

    let n = spots_slice.len();
    if n != strikes_slice.len() || n != ivs_slice.len() || n != is_call_slice.len() {
        return Err(pyo3::exceptions::PyValueError::new_err("Array length mismatch"));
    }

    // 2. Demonstration of processing the native pointers
    let mut black_hole_accumulator = 0.0f32;
    for i in 0..n {
        let spot = spots_slice[i];
        let strk = strikes_slice[i];
        let iv = ivs_slice[i];
        let call = is_call_slice[i];
        
        // Dummy math to prove memory access is valid and fast
        if call {
            black_hole_accumulator += spot * iv - strk;
        } else {
            black_hole_accumulator += strk * iv - spot;
        }
    }

    // Return the length to prove processing completed
    Ok(n as u32)
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_kernel(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(pearson_r, m)?)?;
    m.add_function(wrap_pyfunction!(detect_vanna_flip, m)?)?;
    m.add_function(wrap_pyfunction!(update_vpin_logic, m)?)?;
    m.add_function(wrap_pyfunction!(compute_vol_accel, m)?)?;
    m.add_function(wrap_pyfunction!(compute_from_arrays, m)?)?;
    Ok(())
}

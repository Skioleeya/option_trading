use pyo3::prelude::*;

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

/// A Python module implemented in Rust.
#[pymodule]
fn ndm_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(pearson_r, m)?)?;
    m.add_function(wrap_pyfunction!(detect_vanna_flip, m)?)?;
    Ok(())
}

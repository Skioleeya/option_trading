use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;

fn require_positive_finite(value: f64, name: &str) -> PyResult<f64> {
    if value.is_finite() && value > 0.0 {
        return Ok(value);
    }
    Err(PyValueError::new_err(format!(
        "{name} must be finite and positive"
    )))
}

#[pyfunction]
fn atm_decay_raw_pct(
    anchor_call: f64,
    anchor_put: f64,
    current_call: f64,
    current_put: f64,
) -> PyResult<(f64, f64, f64)> {
    let anchor_c = require_positive_finite(anchor_call, "anchor_call")?;
    let anchor_p = require_positive_finite(anchor_put, "anchor_put")?;
    let current_c = require_positive_finite(current_call, "current_call")?;
    let current_p = require_positive_finite(current_put, "current_put")?;

    let anchor_s = anchor_c + anchor_p;
    let current_s = current_c + current_p;
    if !anchor_s.is_finite() || anchor_s <= 0.0 || !current_s.is_finite() || current_s <= 0.0 {
        return Err(PyValueError::new_err(
            "straddle prices must be finite and positive",
        ));
    }

    Ok((
        (current_c - anchor_c) / anchor_c,
        (current_p - anchor_p) / anchor_p,
        (current_s - anchor_s) / anchor_s,
    ))
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(atm_decay_raw_pct, module)?)?;
    Ok(())
}

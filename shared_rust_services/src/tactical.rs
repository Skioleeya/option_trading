use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};

pub const DEFAULT_VRP_BASELINE_HV_PCT: f64 = 13.5;
const DEFAULT_CHEAP_THRESHOLD: f64 = -2.0;
const DEFAULT_EXPENSIVE_THRESHOLD: f64 = 2.0;
const DEFAULT_TRAP_THRESHOLD: f64 = 5.0;
const VALID_SVOL_STATES: [&str; 5] = [
    "DANGER_ZONE",
    "GRIND_STABLE",
    "VANNA_FLIP",
    "NORMAL",
    "UNAVAILABLE",
];

fn normalize_iv_percent_impl(value: Option<f64>) -> Option<f64> {
    value.and_then(|iv| {
        if !iv.is_finite() {
            return None;
        }
        Some(if iv.abs() <= 3.0 { iv * 100.0 } else { iv })
    })
}

fn normalize_vrp_baseline_hv_pct_impl(value: Option<f64>) -> f64 {
    match value {
        Some(baseline) if baseline.is_finite() && baseline > 0.0 => {
            if baseline <= 1.0 {
                baseline * 100.0
            } else {
                baseline
            }
        }
        _ => DEFAULT_VRP_BASELINE_HV_PCT,
    }
}

fn normalize_guard_vrp_threshold_pct_impl(value: Option<f64>, default_pct: f64) -> f64 {
    match value {
        Some(threshold) if threshold.is_finite() && threshold > 0.0 => {
            if threshold <= 1.0 {
                threshold * 100.0
            } else {
                threshold
            }
        }
        _ => default_pct,
    }
}

fn compute_vrp_impl(atm_iv: Option<f64>, baseline_hv: Option<f64>) -> Option<f64> {
    let atm_iv_pct = normalize_iv_percent_impl(atm_iv)?;
    Some(atm_iv_pct - normalize_vrp_baseline_hv_pct_impl(baseline_hv))
}

fn compute_guard_vrp_proxy_pct_impl(atm_iv: Option<f64>, vol_accel_ratio: Option<f64>) -> Option<f64> {
    let atm_iv_pct = normalize_iv_percent_impl(atm_iv)?;
    let vol_accel = vol_accel_ratio?;
    if !vol_accel.is_finite() {
        return None;
    }
    Some(atm_iv_pct - vol_accel.abs() * 10.0)
}

fn classify_vrp_state_impl(
    vrp: Option<f64>,
    cheap_threshold: Option<f64>,
    expensive_threshold: Option<f64>,
    trap_threshold: Option<f64>,
) -> String {
    let Some(vrp_value) = vrp.filter(|value| value.is_finite()) else {
        return "FAIR".to_string();
    };
    let cheap = cheap_threshold
        .filter(|value| value.is_finite())
        .unwrap_or(DEFAULT_CHEAP_THRESHOLD);
    let expensive = expensive_threshold
        .filter(|value| value.is_finite())
        .unwrap_or(DEFAULT_EXPENSIVE_THRESHOLD);
    let trap = trap_threshold
        .filter(|value| value.is_finite())
        .unwrap_or(DEFAULT_TRAP_THRESHOLD);

    if vrp_value > trap {
        "TRAP".to_string()
    } else if vrp_value > expensive {
        "EXPENSIVE".to_string()
    } else if vrp_value < cheap * 3.0 {
        "BARGAIN".to_string()
    } else if vrp_value < cheap {
        "CHEAP".to_string()
    } else {
        "FAIR".to_string()
    }
}

fn normalize_svol_state_impl(raw_state: Option<&str>) -> String {
    let Some(raw_value) = raw_state else {
        return "UNAVAILABLE".to_string();
    };
    let state = raw_value.rsplit('.').next().unwrap_or(raw_value);
    if VALID_SVOL_STATES.contains(&state) {
        state.to_string()
    } else {
        "NORMAL".to_string()
    }
}

#[pyfunction]
fn tactical_triad_spec(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("DEFAULT_VRP_BASELINE_HV_PCT", DEFAULT_VRP_BASELINE_HV_PCT)?;
    out.set_item("VALID_SVOL_STATES", VALID_SVOL_STATES)?;
    out.set_item("DEFAULT_CHEAP_THRESHOLD", DEFAULT_CHEAP_THRESHOLD)?;
    out.set_item("DEFAULT_EXPENSIVE_THRESHOLD", DEFAULT_EXPENSIVE_THRESHOLD)?;
    out.set_item("DEFAULT_TRAP_THRESHOLD", DEFAULT_TRAP_THRESHOLD)?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (value=None))]
fn tactical_normalize_iv_percent(value: Option<f64>) -> Option<f64> {
    normalize_iv_percent_impl(value)
}

#[pyfunction]
#[pyo3(signature = (value=None))]
fn tactical_normalize_vrp_baseline_hv_pct(value: Option<f64>) -> f64 {
    normalize_vrp_baseline_hv_pct_impl(value)
}

#[pyfunction]
#[pyo3(signature = (value=None, default_pct=None))]
fn tactical_normalize_guard_vrp_threshold_pct(value: Option<f64>, default_pct: Option<f64>) -> f64 {
    normalize_guard_vrp_threshold_pct_impl(value, default_pct.unwrap_or(DEFAULT_VRP_BASELINE_HV_PCT))
}

#[pyfunction]
#[pyo3(signature = (atm_iv=None, baseline_hv=None))]
fn tactical_compute_vrp(atm_iv: Option<f64>, baseline_hv: Option<f64>) -> Option<f64> {
    compute_vrp_impl(atm_iv, baseline_hv)
}

#[pyfunction]
#[pyo3(signature = (atm_iv=None, vol_accel_ratio=None))]
fn tactical_compute_guard_vrp_proxy_pct(
    atm_iv: Option<f64>,
    vol_accel_ratio: Option<f64>,
) -> Option<f64> {
    compute_guard_vrp_proxy_pct_impl(atm_iv, vol_accel_ratio)
}

#[pyfunction]
#[pyo3(signature = (vrp=None, cheap_threshold=None, expensive_threshold=None, trap_threshold=None))]
fn tactical_classify_vrp_state(
    vrp: Option<f64>,
    cheap_threshold: Option<f64>,
    expensive_threshold: Option<f64>,
    trap_threshold: Option<f64>,
) -> String {
    classify_vrp_state_impl(vrp, cheap_threshold, expensive_threshold, trap_threshold)
}

#[pyfunction]
#[pyo3(signature = (raw_state=None))]
fn tactical_normalize_svol_state(raw_state: Option<&str>) -> String {
    normalize_svol_state_impl(raw_state)
}

#[pyfunction]
#[pyo3(signature = (vanna_result=None))]
fn tactical_resolve_svol_fields(py: Python<'_>, vanna_result: Option<PyObject>) -> PyResult<(Option<f64>, String)> {
    let Some(result) = vanna_result else {
        return Ok((None, "UNAVAILABLE".to_string()));
    };
    let result = result.bind(py);
    let state_str: Option<String> = match result.getattr("state") {
        Ok(state_obj) if !state_obj.is_none() => match state_obj.getattr("value") {
            Ok(v) if !v.is_none() => v.str().ok().map(|s| s.to_string()),
            _ => state_obj.str().ok().map(|s| s.to_string()),
        },
        _ => None,
    };
    let state = normalize_svol_state_impl(state_str.as_deref());
    let corr: Option<f64> = match result.getattr("correlation") {
        Ok(c) if !c.is_none() => c.extract::<f64>().ok().filter(|v| v.is_finite()),
        _ => None,
    };
    match corr {
        None => Ok((None, "UNAVAILABLE".to_string())),
        Some(c) => Ok((Some(c), state)),
    }
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(tactical_triad_spec, module)?)?;
    module.add_function(wrap_pyfunction!(tactical_normalize_iv_percent, module)?)?;
    module.add_function(wrap_pyfunction!(tactical_normalize_vrp_baseline_hv_pct, module)?)?;
    module.add_function(wrap_pyfunction!(tactical_normalize_guard_vrp_threshold_pct, module)?)?;
    module.add_function(wrap_pyfunction!(tactical_compute_vrp, module)?)?;
    module.add_function(wrap_pyfunction!(tactical_compute_guard_vrp_proxy_pct, module)?)?;
    module.add_function(wrap_pyfunction!(tactical_classify_vrp_state, module)?)?;
    module.add_function(wrap_pyfunction!(tactical_normalize_svol_state, module)?)?;
    module.add_function(wrap_pyfunction!(tactical_resolve_svol_fields, module)?)?;
    Ok(())
}

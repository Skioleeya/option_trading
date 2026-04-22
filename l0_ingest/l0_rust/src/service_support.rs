use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};

const COLUMNAR_SCHEMA_VERSION: &str = "v2";
const COLUMNAR_ENCODING: &str = "columnar-json";

const VALID_VIEWS: [&str; 3] = ["compact", "feature", "audit"];
const VALID_INTERVALS: [(&str, u64); 3] = [("1s", 1), ("5s", 5), ("1m", 60)];
const VALID_FORMATS: [&str; 2] = ["jsonl", "parquet"];

const COMPACT_FIELDS: [&str; 18] = [
    "data_timestamp",
    "as_of_utc",
    "l0_version",
    "symbol",
    "spot",
    "atm_iv",
    "net_gex",
    "call_wall",
    "put_wall",
    "flip_level",
    "bbo_imbalance_raw",
    "direction_code",
    "iv_regime_code",
    "gex_intensity_code",
    "confidence",
    "max_impact",
    "dealer_squeeze_alert",
    "stored_at",
];

const FEATURE_FIELDS: [&str; 37] = [
    "data_timestamp", "as_of_utc", "l0_version", "symbol", "spot", "atm_iv",
    "net_gex", "call_wall", "put_wall", "flip_level", "bbo_imbalance_raw", "session_phase",
    "skew_25d_normalized", "rr25_call_minus_put", "realized_volatility_15m",
    "vol_risk_premium", "vrp_realized_based", "longport_official_hv_decimal",
    "longport_official_hv_sample_count", "longport_official_hv_age_sec",
    "vrp_official_hv_based", "direction_code", "iv_regime_code", "gex_intensity_code", "confidence",
    "max_impact", "dealer_squeeze_alert", "net_delta_exposure_live", "net_gamma_exposure_live",
    "residual_delta_after_netting", "oi_participation_ratio_live", "flow_suppression_bias",
    "flow_dominance_ratio", "midpoint_tickrule_count", "condition_filtered_count",
    "complex_spread_count", "stored_at",
];

const LABEL_FIELDS: [&str; 11] = [
    "data_timestamp",
    "l0_version",
    "symbol",
    "fwd_ret_1m",
    "fwd_ret_5m",
    "fwd_ret_15m",
    "fwd_ret_60m",
    "max_adverse_excursion",
    "realized_vol_horizon",
    "horizon_observed_seconds",
    "stored_at",
];

fn mapping_item<'py>(row: &Bound<'py, PyAny>, key: &str) -> PyResult<Option<Bound<'py, PyAny>>> {
    let value = row.call_method1("get", (key,))?;
    if value.is_none() {
        return Ok(None);
    }
    Ok(Some(value))
}

fn append_list<'py>(py: Python<'py>, values: &[&str]) -> PyResult<Bound<'py, PyList>> {
    let out = PyList::empty(py);
    for value in values {
        out.append(*value)?;
    }
    Ok(out)
}

fn normalize_positive(value: Option<f64>) -> Option<f64> {
    match value {
        Some(inner) if inner.is_finite() && inner > 0.0 => Some(inner),
        _ => None,
    }
}

#[pyfunction]
fn service_pack_rows_columnar(py: Python<'_>, rows: Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    let columns = PyList::empty(py);
    let seen = PyDict::new(py);
    let matrix = PyList::empty(py);

    for item in rows.try_iter()? {
        let row = item?;
        for key_obj in row.call_method0("keys")?.try_iter()? {
            let key = key_obj?.extract::<String>()?;
            if !seen.contains(&key)? {
                seen.set_item(&key, true)?;
                columns.append(&key)?;
            }
        }
    }

    for item in rows.try_iter()? {
        let row = item?;
        let packed = PyList::empty(py);
        for column in columns.iter() {
            let key = column.extract::<String>()?;
            match mapping_item(&row, &key)? {
                Some(value) => packed.append(value)?,
                None => packed.append(py.None())?,
            }
        }
        matrix.append(packed)?;
    }

    Ok((columns, matrix).into_pyobject(py)?.unbind().into())
}

#[pyfunction]
#[pyo3(signature = (current=None, *, closes, min_history_days=5))]
fn service_header_compute_ivr(
    current: Option<f64>,
    closes: Vec<f64>,
    min_history_days: usize,
) -> Option<f64> {
    let current_value = normalize_positive(current)?;
    if closes.len() < min_history_days {
        return None;
    }
    let min_iv = closes.iter().copied().fold(f64::INFINITY, f64::min);
    let max_iv = closes.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let span = max_iv - min_iv;
    if span <= 1e-9 {
        return Some(if current_value > max_iv {
            100.0
        } else if current_value < min_iv {
            0.0
        } else {
            50.0
        });
    }
    Some(((current_value - min_iv) / span) * 100.0)
}

#[pyfunction]
#[pyo3(signature = (current=None, *, closes, min_history_days=5))]
fn service_header_compute_ivp(
    current: Option<f64>,
    closes: Vec<f64>,
    min_history_days: usize,
) -> Option<f64> {
    let current_value = normalize_positive(current)?;
    if closes.len() < min_history_days {
        return None;
    }
    let lower_days = closes.iter().filter(|value| **value < current_value).count();
    Some((lower_days as f64 / closes.len() as f64) * 100.0)
}

#[pyfunction]
#[pyo3(signature = (current=None, anchor=None))]
fn service_header_safe_ratio(current: Option<f64>, anchor: Option<f64>) -> Option<f64> {
    let current_value = normalize_positive(current)?;
    let anchor_value = normalize_positive(anchor)?;
    Some(current_value / anchor_value)
}

#[pyfunction]
#[pyo3(signature = (ratio=None))]
fn service_header_term_state(ratio: Option<f64>) -> String {
    match ratio {
        None => "UNAVAILABLE".to_string(),
        Some(inner) if inner > 1.05 => "INVERTED".to_string(),
        Some(inner) if inner >= 0.95 => "FLAT".to_string(),
        Some(_) => "NORMAL".to_string(),
    }
}

#[pyfunction]
fn service_research_schema_spec(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    let valid_intervals = PyDict::new(py);
    for (key, value) in VALID_INTERVALS {
        valid_intervals.set_item(key, value)?;
    }
    out.set_item("valid_views", append_list(py, &VALID_VIEWS)?)?;
    out.set_item("valid_formats", append_list(py, &VALID_FORMATS)?)?;
    out.set_item("valid_intervals", valid_intervals)?;
    out.set_item("compact_fields", append_list(py, &COMPACT_FIELDS)?)?;
    out.set_item("feature_fields", append_list(py, &FEATURE_FIELDS)?)?;
    out.set_item("label_fields", append_list(py, &LABEL_FIELDS)?)?;
    out.set_item("columnar_schema_version", COLUMNAR_SCHEMA_VERSION)?;
    out.set_item("columnar_encoding", COLUMNAR_ENCODING)?;
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(service_pack_rows_columnar, module)?)?;
    module.add_function(wrap_pyfunction!(service_header_compute_ivr, module)?)?;
    module.add_function(wrap_pyfunction!(service_header_compute_ivp, module)?)?;
    module.add_function(wrap_pyfunction!(service_header_safe_ratio, module)?)?;
    module.add_function(wrap_pyfunction!(service_header_term_state, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_schema_spec, module)?)?;
    Ok(())
}

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};

const VALID_VIEWS: [&str; 3] = ["compact", "feature", "audit"];
const VALID_FORMATS: [&str; 2] = ["jsonl", "parquet"];
const VALID_INTERVALS: [(&str, i64); 3] = [("1s", 1), ("5s", 5), ("1m", 60)];
const COMPACT_FIELDS: [&str; 16] = [
    "data_timestamp", "as_of_utc", "l0_version", "symbol", "spot", "atm_iv", "net_gex",
    "call_wall", "put_wall", "flip_level", "direction", "confidence", "gex_intensity",
    "iv_regime", "vpin_composite", "bbo_imbalance_raw",
];
const FEATURE_FIELDS: [&str; 57] = [
    "data_timestamp", "as_of_utc", "l0_version", "symbol", "spot", "atm_iv", "net_gex",
    "net_vanna_raw_sum", "net_vanna", "net_charm_raw_sum", "net_charm", "call_wall", "put_wall",
    "flip_level", "vpin_1m", "vpin_5m", "vpin_15m", "vpin_composite", "bbo_imbalance_raw",
    "bbo_ewma_fast", "bbo_ewma_slow", "bbo_persistence", "vol_accel_ratio", "vol_accel_threshold",
    "vol_accel_elevated", "vol_entropy", "session_phase", "mtf_consensus", "mtf_alignment",
    "mtf_strength", "stored_at", "skew_25d_normalized", "rr25_call_minus_put",
    "realized_volatility_15m", "vol_risk_premium", "vrp_realized_based",
    "longport_tier2_contracts", "longport_tier3_contracts",
    "longport_tier2_standard_ratio", "longport_tier3_standard_ratio",
    "longport_tier2_avg_premium", "longport_tier3_avg_premium",
    "longport_official_hv_decimal", "longport_official_hv_sample_count",
    "longport_official_hv_age_sec", "vrp_official_hv_based", "direction",
    "confidence", "pre_guard_direction", "guard_actions_json", "fusion_weights_json",
    "signal_summary_json", "feature_vector_json", "iv_regime", "gex_intensity",
    "max_impact", "dealer_squeeze_alert",
];
const LABEL_FIELDS: [&str; 8] = [
    "fwd_ret_1m", "fwd_ret_5m", "fwd_ret_15m", "fwd_ret_60m", "max_adverse_excursion",
    "realized_vol_horizon", "horizon_observed_seconds", "stored_at",
];

fn build_schema(py: Python<'_>, fields: &[(&str, &str)]) -> PyResult<Py<PyAny>> {
    let pa = py.import("pyarrow")?;
    let list = PyList::empty(py);
    for (name, pa_type) in fields {
        let typ = pa.getattr(*pa_type)?.call0()?;
        list.append((*name, typ))?;
    }
    Ok(pa.getattr("schema")?.call1((list,))?.unbind())
}

#[pyfunction]
fn research_valid_views() -> Vec<&'static str> {
    VALID_VIEWS.to_vec()
}

#[pyfunction]
fn research_valid_formats() -> Vec<&'static str> {
    VALID_FORMATS.to_vec()
}

#[pyfunction]
fn research_valid_intervals(py: Python<'_>) -> Py<PyDict> {
    let dict = PyDict::new(py);
    for (key, value) in VALID_INTERVALS {
        let _ = dict.set_item(key, value);
    }
    dict.unbind()
}

#[pyfunction]
fn research_compact_fields() -> Vec<&'static str> {
    COMPACT_FIELDS.to_vec()
}

#[pyfunction]
fn research_feature_fields() -> Vec<&'static str> {
    FEATURE_FIELDS.to_vec()
}

#[pyfunction]
fn research_label_fields() -> Vec<&'static str> {
    LABEL_FIELDS.to_vec()
}

#[pyfunction]
fn research_raw_schema(py: Python<'_>) -> PyResult<Py<PyAny>> {
    build_schema(py, &[
        ("data_timestamp", "string"), ("as_of_utc", "string"), ("l0_version", "int64"),
        ("symbol", "string"), ("spot", "float64"), ("atm_iv", "float64"), ("net_gex", "float64"),
        ("net_vanna_raw_sum", "float64"), ("net_vanna", "float64"), ("net_charm_raw_sum", "float64"),
        ("net_charm", "float64"), ("call_wall", "float64"), ("put_wall", "float64"),
        ("flip_level", "float64"), ("vpin_1m", "float64"), ("vpin_5m", "float64"),
        ("vpin_15m", "float64"), ("vpin_composite", "float64"), ("bbo_imbalance_raw", "float64"),
        ("bbo_ewma_fast", "float64"), ("bbo_ewma_slow", "float64"), ("bbo_persistence", "float64"),
        ("vol_accel_ratio", "float64"), ("vol_accel_threshold", "float64"), ("vol_accel_elevated", "bool_"),
        ("vol_entropy", "float64"), ("session_phase", "string"), ("mtf_consensus", "string"),
        ("mtf_alignment", "float64"), ("mtf_strength", "float64"), ("stored_at", "string"),
    ])
}

#[pyfunction]
fn research_feature_schema(py: Python<'_>) -> PyResult<Py<PyAny>> {
    build_schema(py, &[
        ("data_timestamp", "string"), ("as_of_utc", "string"), ("l0_version", "int64"),
        ("symbol", "string"), ("spot", "float64"), ("atm_iv", "float64"), ("net_gex", "float64"),
        ("net_vanna_raw_sum", "float64"), ("net_vanna", "float64"), ("net_charm_raw_sum", "float64"),
        ("net_charm", "float64"), ("call_wall", "float64"), ("put_wall", "float64"),
        ("flip_level", "float64"), ("vpin_1m", "float64"), ("vpin_5m", "float64"),
        ("vpin_15m", "float64"), ("vpin_composite", "float64"), ("bbo_imbalance_raw", "float64"),
        ("bbo_ewma_fast", "float64"), ("bbo_ewma_slow", "float64"), ("bbo_persistence", "float64"),
        ("vol_accel_ratio", "float64"), ("vol_accel_threshold", "float64"), ("vol_accel_elevated", "bool_"),
        ("vol_entropy", "float64"), ("session_phase", "string"), ("mtf_consensus", "string"),
        ("mtf_alignment", "float64"), ("mtf_strength", "float64"), ("stored_at", "string"),
        ("skew_25d_normalized", "float64"), ("rr25_call_minus_put", "float64"),
        ("realized_volatility_15m", "float64"), ("vol_risk_premium", "float64"),
        ("vrp_realized_based", "float64"), ("longport_tier2_contracts", "int64"),
        ("longport_tier3_contracts", "int64"), ("longport_tier2_standard_ratio", "float64"),
        ("longport_tier3_standard_ratio", "float64"), ("longport_tier2_avg_premium", "float64"),
        ("longport_tier3_avg_premium", "float64"), ("longport_official_hv_decimal", "float64"),
        ("longport_official_hv_sample_count", "int64"), ("longport_official_hv_age_sec", "float64"),
        ("vrp_official_hv_based", "float64"), ("direction", "string"), ("confidence", "float64"),
        ("pre_guard_direction", "string"), ("guard_actions_json", "string"), ("fusion_weights_json", "string"),
        ("signal_summary_json", "string"), ("feature_vector_json", "string"), ("iv_regime", "string"),
        ("gex_intensity", "string"), ("max_impact", "float64"), ("dealer_squeeze_alert", "bool_"),
    ])
}

#[pyfunction]
fn research_label_schema(py: Python<'_>) -> PyResult<Py<PyAny>> {
    build_schema(py, &[
        ("data_timestamp", "string"), ("l0_version", "int64"), ("symbol", "string"),
        ("fwd_ret_1m", "float64"), ("fwd_ret_5m", "float64"), ("fwd_ret_15m", "float64"),
        ("fwd_ret_60m", "float64"), ("max_adverse_excursion", "float64"),
        ("realized_vol_horizon", "float64"), ("horizon_observed_seconds", "float64"),
        ("stored_at", "string"),
    ])
}

#[pyfunction]
fn research_tier_schema(py: Python<'_>, tier_name: &str) -> PyResult<Py<PyAny>> {
    match tier_name {
        "raw" => research_raw_schema(py),
        "feature" => research_feature_schema(py),
        "label" => research_label_schema(py),
        _ => Err(PyValueError::new_err(format!("unknown tier schema: {tier_name}"))),
    }
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(research_valid_views, m)?)?;
    m.add_function(wrap_pyfunction!(research_valid_formats, m)?)?;
    m.add_function(wrap_pyfunction!(research_valid_intervals, m)?)?;
    m.add_function(wrap_pyfunction!(research_compact_fields, m)?)?;
    m.add_function(wrap_pyfunction!(research_feature_fields, m)?)?;
    m.add_function(wrap_pyfunction!(research_label_fields, m)?)?;
    m.add_function(wrap_pyfunction!(research_raw_schema, m)?)?;
    m.add_function(wrap_pyfunction!(research_feature_schema, m)?)?;
    m.add_function(wrap_pyfunction!(research_label_schema, m)?)?;
    m.add_function(wrap_pyfunction!(research_tier_schema, m)?)?;
    Ok(())
}

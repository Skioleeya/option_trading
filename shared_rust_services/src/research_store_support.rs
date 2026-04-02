use chrono::{DateTime, Duration, NaiveDate, Utc};
use chrono_tz::US::Eastern;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

pub const VALID_VIEWS: [&str; 3] = ["compact", "feature", "audit"];
pub const VALID_FORMATS: [&str; 2] = ["jsonl", "parquet"];
pub const VALID_INTERVALS: [(&str, i64); 3] = [("1s", 1), ("5s", 5), ("1m", 60)];

pub fn parse_ts_text(text: &str) -> Option<DateTime<Utc>> {
    let normalized = if text.ends_with('Z') {
        format!("{}+00:00", &text[..text.len() - 1])
    } else {
        text.to_string()
    };
    DateTime::parse_from_rfc3339(&normalized).ok().map(|dt| dt.with_timezone(&Utc))
}

pub fn parse_ts_any(raw: &Bound<'_, PyAny>) -> PyResult<Option<DateTime<Utc>>> {
    if raw.is_none() {
        return Ok(None);
    }
    if let Ok(text) = raw.extract::<String>() {
        return Ok(parse_ts_text(text.trim()));
    }
    let py = raw.py();
    let datetime = py.import("datetime")?.getattr("datetime")?;
    if raw.is_instance(&datetime)? {
        let timezone = py.import("datetime")?.getattr("timezone")?.getattr("utc")?;
        let utc_dt = raw.call_method1("astimezone", (timezone,))?;
        let iso = utc_dt.call_method0("isoformat")?.extract::<String>()?;
        return Ok(parse_ts_text(&iso));
    }
    Ok(None)
}

pub fn et_date(ts: DateTime<Utc>) -> String {
    ts.with_timezone(&Eastern).format("%Y%m%d").to_string()
}

pub fn utc_iso(ts: DateTime<Utc>) -> String {
    ts.to_rfc3339()
}

pub fn dict_to_hashmap(dict: &Bound<'_, PyDict>) -> PyResult<HashMap<String, Py<PyAny>>> {
    let mut out = HashMap::new();
    for (key, value) in dict.iter() {
        out.insert(key.extract::<String>()?, value.unbind());
    }
    Ok(out)
}

pub fn py_none<'py>(py: Python<'py>) -> Py<PyAny> {
    py.None()
}

pub fn settings_value<T>(py: Python<'_>, name: &str, default: T) -> PyResult<T>
where
    T: for<'a> FromPyObject<'a> + Clone,
{
    let settings = py.import("shared.config")?.getattr("settings")?;
    Ok(settings.getattr(name)?.extract::<T>().unwrap_or(default))
}

pub fn l0_rust<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
    Ok(py.import("shared.services.l0_runtime._native_generated")?.getattr("l0_rust")?)
}

pub fn shared_services<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyModule>> {
    py.import("shared_rust.services")
}

pub fn tier_schema(py: Python<'_>, tier_name: &str) -> PyResult<Py<PyAny>> {
    Ok(shared_services(py)?.getattr("research_tier_schema")?.call1((tier_name,))?.unbind())
}

pub fn ensure_dirs(root: &Path) -> std::io::Result<(PathBuf, PathBuf, PathBuf, PathBuf)> {
    let raw = root.join("raw");
    let feature = root.join("feature");
    let label = root.join("label");
    let export = root.join("exports");
    for path in [&raw, &feature, &label, &export] {
        fs::create_dir_all(path)?;
    }
    Ok((raw, feature, label, export))
}

pub fn cleanup_tier_path(tier_dir: &Path, prefix: &str, now_et_date: NaiveDate, retention_days: i64) -> PyResult<()> {
    let cutoff = now_et_date - Duration::days(retention_days.max(1));
    let cutoff_date = cutoff.format("%Y%m%d").to_string();
    let names: Vec<String> = fs::read_dir(tier_dir)
        .map_err(|err| PyValueError::new_err(err.to_string()))?
        .filter_map(Result::ok)
        .filter_map(|entry| entry.file_name().into_string().ok())
        .collect();
    Python::with_gil(|py| -> PyResult<()> {
        let native = l0_rust(py)?;
        let candidates = native.call_method1("service_research_retention_candidates", (names, prefix, cutoff_date))?;
        for value in candidates.downcast::<PyList>()?.iter() {
            let name = value.extract::<String>()?;
            let path = tier_dir.join(name);
            let _ = fs::remove_file(path);
        }
        Ok(())
    })
}

pub fn project_allowed(view: &str) -> &'static [&'static str] {
    const COMPACT: &[&str] = &[
        "data_timestamp", "as_of_utc", "l0_version", "symbol", "spot", "atm_iv", "net_gex",
        "call_wall", "put_wall", "flip_level", "direction", "confidence", "gex_intensity",
        "iv_regime", "vpin_composite", "bbo_imbalance_raw",
    ];
    const FEATURE: &[&str] = &[
        "data_timestamp", "as_of_utc", "l0_version", "symbol", "spot", "atm_iv", "net_gex",
        "net_vanna_raw_sum", "net_vanna", "net_charm_raw_sum", "net_charm", "call_wall", "put_wall",
        "flip_level", "vpin_1m", "vpin_5m", "vpin_15m", "vpin_composite", "bbo_imbalance_raw",
        "bbo_ewma_fast", "bbo_ewma_slow", "bbo_persistence", "vol_accel_ratio", "vol_accel_threshold",
        "vol_accel_elevated", "vol_entropy", "session_phase", "mtf_consensus", "mtf_alignment",
        "mtf_strength", "stored_at", "skew_25d_normalized", "rr25_call_minus_put",
        "realized_volatility_15m", "vol_risk_premium", "vrp_realized_based",
        "longport_tier2_contracts", "longport_tier3_contracts", "longport_tier2_standard_ratio",
        "longport_tier3_standard_ratio", "longport_tier2_avg_premium", "longport_tier3_avg_premium",
        "longport_official_hv_decimal", "longport_official_hv_sample_count", "longport_official_hv_age_sec",
        "vrp_official_hv_based", "direction", "confidence", "pre_guard_direction", "guard_actions_json",
        "fusion_weights_json", "signal_summary_json", "feature_vector_json", "iv_regime", "gex_intensity",
        "max_impact", "dealer_squeeze_alert", "fwd_ret_1m", "fwd_ret_5m", "fwd_ret_15m", "fwd_ret_60m",
        "max_adverse_excursion", "realized_vol_horizon", "horizon_observed_seconds",
    ];
    if view == "compact" { COMPACT } else { FEATURE }
}

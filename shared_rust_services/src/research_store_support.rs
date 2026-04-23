use chrono::{DateTime, Duration, NaiveDate, Timelike, Utc};
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
    Ok(py.import("shared.services.l0_runtime.native_loader")?.getattr("l0_rust")?)
}

pub fn shared_services<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyModule>> {
    py.import("shared_rust.services")
}

pub fn tier_schema(py: Python<'_>, tier_name: &str) -> PyResult<Py<PyAny>> {
    Ok(shared_services(py)?.getattr("research_tier_schema")?.call1((tier_name,))?.unbind())
}

pub fn ensure_dirs(root: &Path) -> std::io::Result<(PathBuf, PathBuf)> {
    let canonical = root.join("canonical");
    let export = root.join("exports");
    for path in [&canonical, &export] {
        fs::create_dir_all(path)?;
    }
    Ok((canonical, export))
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
        "call_wall", "put_wall", "flip_level", "bbo_imbalance_raw", "direction_code",
        "iv_regime_code", "gex_intensity_code", "confidence", "max_impact",
        "dealer_squeeze_alert", "stored_at",
    ];
    const FEATURE: &[&str] = &[
        "data_timestamp", "as_of_utc", "l0_version", "symbol", "spot", "atm_iv", "net_gex",
        "call_wall", "put_wall", "flip_level", "bbo_imbalance_raw", "session_phase",
        "skew_25d_normalized", "rr25_call_minus_put", "realized_volatility_15m",
        "vol_risk_premium", "vrp_realized_based", "longport_official_hv_decimal",
        "longport_official_hv_sample_count", "longport_official_hv_age_sec",
        "vrp_official_hv_based", "direction_code", "iv_regime_code", "gex_intensity_code",
        "confidence", "max_impact", "dealer_squeeze_alert", "net_delta_exposure_live",
        "net_gamma_exposure_live", "residual_delta_after_netting", "oi_participation_ratio_live",
        "flow_suppression_bias", "flow_dominance_ratio", "midpoint_tickrule_count",
        "condition_filtered_count", "complex_spread_count", "stored_at", "fwd_ret_1m",
        "fwd_ret_5m", "fwd_ret_15m", "fwd_ret_60m", "max_adverse_excursion", "realized_vol_horizon",
        "horizon_observed_seconds",
    ];
    if view == "compact" { COMPACT } else { FEATURE }
}

pub fn is_rth(ts: DateTime<Utc>) -> bool {
    let et = ts.with_timezone(&Eastern);
    let minute_of_day = et.hour() as i32 * 60 + et.minute() as i32;
    (9 * 60 + 30..16 * 60).contains(&minute_of_day)
}

pub fn direction_to_code(direction: &str) -> i8 {
    match direction.trim().to_ascii_uppercase().as_str() {
        "BULLISH" => 1,
        "BEARISH" => -1,
        "HALT" => 2,
        "NO_TRADE" => 3,
        _ => 0,
    }
}

pub fn iv_regime_to_code(iv_regime: &str) -> i8 {
    match iv_regime.trim().to_ascii_uppercase().as_str() {
        "VERY_LOW" => -2,
        "LOW" => -1,
        "NORMAL" => 0,
        "ELEVATED" => 1,
        "HIGH" => 2,
        "EXTREME" | "CRISIS" => 3,
        _ => 0,
    }
}

pub fn gex_intensity_to_code(gex_intensity: &str) -> i8 {
    match gex_intensity.trim().to_ascii_uppercase().as_str() {
        "EXTREME_NEGATIVE" => -3,
        "STRONG_NEGATIVE" => -2,
        "NEGATIVE" => -1,
        "NEUTRAL" => 0,
        "POSITIVE" => 1,
        "STRONG_POSITIVE" => 2,
        "EXTREME_POSITIVE" => 3,
        _ => 0,
    }
}

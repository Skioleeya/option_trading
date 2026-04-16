use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};
use std::collections::HashSet;

fn mapping_item<'py>(row: &Bound<'py, PyAny>, key: &str) -> PyResult<Bound<'py, PyAny>> {
    row.call_method1("get", (key,))
}

fn valid_trade_date(name: &str, prefix: &str) -> Option<String> {
    let stem = name.strip_suffix(".parquet").unwrap_or(name);
    let expected_prefix = format!("{prefix}_");
    let date_part = stem.strip_prefix(&expected_prefix)?;
    if date_part.len() != 8 || !date_part.chars().all(|ch| ch.is_ascii_digit()) {
        return None;
    }
    Some(date_part.to_string())
}

fn valid_trade_file(name: &str, prefix: &str) -> Option<(String, String)> {
    let date_part = valid_trade_date(name, prefix)?;
    Some((name.to_string(), date_part))
}

fn mapping_f64(row: &Bound<'_, PyAny>, key: &str) -> Option<f64> {
    mapping_item(row, key)
        .ok()
        .and_then(|value| value.extract::<Option<f64>>().ok())
        .flatten()
        .filter(|value| value.is_finite())
}

fn mapping_i64(row: &Bound<'_, PyAny>, key: &str) -> Option<i64> {
    mapping_item(row, key)
        .ok()
        .and_then(|value| value.extract::<Option<i64>>().ok())
        .flatten()
}

#[pyfunction]
fn service_research_to_compact_record(py: Python<'_>, row: Bound<'_, PyAny>) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    let keys = [
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
    for key in keys {
        out.set_item(key, mapping_item(&row, key)?)?;
    }
    Ok(out.unbind())
}

#[pyfunction]
fn service_research_project_records(
    py: Python<'_>,
    records: Bound<'_, PyAny>,
    requested: Vec<String>,
    allowed: Vec<String>,
    max_fields: usize,
) -> PyResult<Py<PyAny>> {
    if requested.is_empty() {
        return Ok(records.unbind());
    }
    if requested.len() > max_fields {
        let out = PyDict::new(py);
        out.set_item(
            "error",
            format!("too many fields requested: {} > {}", requested.len(), max_fields),
        )?;
        return Ok(out.unbind().into());
    }

    let allowed_set: HashSet<&str> = allowed.iter().map(String::as_str).collect();
    let mut unknown = Vec::new();
    for field in &requested {
        if !allowed_set.contains(field.as_str()) {
            unknown.push(field.clone());
        }
    }
    if !unknown.is_empty() {
        unknown.sort();
        let out = PyDict::new(py);
        out.set_item("error", format!("unknown fields: {}", unknown.join(",")))?;
        return Ok(out.unbind().into());
    }

    let projected = PyList::empty(py);
    for item in records.try_iter()? {
        let row = item?;
        let out_row = PyDict::new(py);
        for field in &requested {
            out_row.set_item(field, mapping_item(&row, field)?)?;
        }
        projected.append(out_row)?;
    }
    Ok(projected.unbind().into())
}

#[pyfunction]
fn service_research_apply_interval(
    py: Python<'_>,
    records: Bound<'_, PyAny>,
    step: u64,
) -> PyResult<Py<PyList>> {
    let out = PyList::empty(py);
    if step <= 1 {
        for item in records.try_iter()? {
            out.append(item?)?;
        }
        return Ok(out.unbind());
    }

    let mut last_bucket: Option<i64> = None;
    let mut last_direction_code: Option<i64> = None;
    for item in records.try_iter()? {
        let row = item?;
        let timestamp = mapping_item(&row, "data_timestamp")?;
        let direction_code = mapping_item(&row, "direction_code")?.extract::<Option<i64>>().ok().flatten();
        let parsed = timestamp.call_method0("timestamp");
        let bucket = match parsed {
            Ok(value) => value.extract::<f64>().ok().map(|inner| (inner / step as f64).floor() as i64),
            Err(_) => None,
        };
        let event_keep = last_direction_code.is_some_and(|prev| Some(prev) != direction_code);
        if event_keep || bucket != last_bucket {
            out.append(&row)?;
            last_bucket = bucket;
            last_direction_code = direction_code;
        }
    }
    Ok(out.unbind())
}

#[pyfunction]
fn service_research_jsonl_bytes(py: Python<'_>, records: Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
    let json = py.import("json")?;
    let mut out = Vec::<u8>::new();
    for item in records.try_iter()? {
        let row = item?;
        let dumped = json.call_method1("dumps", (&row,))?.extract::<String>()?;
        out.extend_from_slice(dumped.as_bytes());
        out.push(b'\n');
    }
    Ok(out)
}

#[pyfunction]
fn service_research_retention_candidates(
    names: Vec<String>,
    prefix: String,
    cutoff_date: String,
) -> Vec<String> {
    let mut out = Vec::new();
    for name in names {
        let Some(date_part) = valid_trade_date(&name, &prefix) else {
            continue;
        };
        if date_part < cutoff_date {
            out.push(name);
        }
    }
    out.sort();
    out
}

#[pyfunction]
fn service_research_range_files(
    names: Vec<String>,
    prefix: String,
    start_date: String,
    end_date: String,
) -> Vec<String> {
    let mut out = Vec::new();
    for name in names {
        let Some((file_name, date_part)) = valid_trade_file(&name, &prefix) else {
            continue;
        };
        if date_part >= start_date && date_part <= end_date {
            out.push(file_name);
        }
    }
    out.sort();
    out
}

#[pyfunction]
fn service_research_latest_files(names: Vec<String>, prefix: String) -> Vec<String> {
    let mut out = Vec::new();
    for name in names {
        let Some((file_name, _)) = valid_trade_file(&name, &prefix) else {
            continue;
        };
        out.push(file_name);
    }
    out.sort_by(|left, right| right.cmp(left));
    out
}

#[pyfunction]
fn service_research_longport_columns(py: Python<'_>, diagnostics: Bound<'_, PyAny>) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("longport_tier2_contracts", mapping_i64(&diagnostics, "tier2_contracts").unwrap_or(0))?;
    out.set_item("longport_tier3_contracts", mapping_i64(&diagnostics, "tier3_contracts").unwrap_or(0))?;
    out.set_item("longport_tier2_standard_ratio", mapping_f64(&diagnostics, "tier2_standard_ratio"))?;
    out.set_item("longport_tier3_standard_ratio", mapping_f64(&diagnostics, "tier3_standard_ratio"))?;
    out.set_item("longport_tier2_avg_premium", mapping_f64(&diagnostics, "tier2_avg_premium"))?;
    out.set_item("longport_tier3_avg_premium", mapping_f64(&diagnostics, "tier3_avg_premium"))?;
    out.set_item("longport_official_hv_decimal", mapping_f64(&diagnostics, "official_hv_decimal"))?;
    out.set_item(
        "longport_official_hv_sample_count",
        mapping_i64(&diagnostics, "official_hv_sample_count").unwrap_or(0),
    )?;
    out.set_item("longport_official_hv_age_sec", mapping_f64(&diagnostics, "official_hv_age_sec"))?;
    Ok(out.unbind())
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(signature = (data_timestamp, l0_version, symbol, stored_at, fwd_ret_1m=None, fwd_ret_5m=None, fwd_ret_15m=None, fwd_ret_60m=None, max_adverse_excursion=None, realized_vol_horizon=None, horizon_observed_seconds=None))]
fn service_research_label_row(
    py: Python<'_>,
    data_timestamp: String,
    l0_version: i64,
    symbol: String,
    stored_at: String,
    fwd_ret_1m: Option<f64>,
    fwd_ret_5m: Option<f64>,
    fwd_ret_15m: Option<f64>,
    fwd_ret_60m: Option<f64>,
    max_adverse_excursion: Option<f64>,
    realized_vol_horizon: Option<f64>,
    horizon_observed_seconds: Option<f64>,
) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("data_timestamp", data_timestamp)?;
    out.set_item("l0_version", l0_version)?;
    out.set_item("symbol", symbol)?;
    out.set_item("fwd_ret_1m", fwd_ret_1m)?;
    out.set_item("fwd_ret_5m", fwd_ret_5m)?;
    out.set_item("fwd_ret_15m", fwd_ret_15m)?;
    out.set_item("fwd_ret_60m", fwd_ret_60m)?;
    out.set_item("max_adverse_excursion", max_adverse_excursion)?;
    out.set_item("realized_vol_horizon", realized_vol_horizon)?;
    out.set_item("horizon_observed_seconds", horizon_observed_seconds)?;
    out.set_item("stored_at", stored_at)?;
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(service_research_to_compact_record, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_project_records, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_apply_interval, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_jsonl_bytes, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_retention_candidates, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_range_files, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_latest_files, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_longport_columns, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_label_row, module)?)?;
    Ok(())
}

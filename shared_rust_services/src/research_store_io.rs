use crate::research_store_support::{et_date, l0_rust, parse_ts_any};
use chrono::{DateTime, Utc};
use pyo3::{exceptions::PyValueError, prelude::*, types::{PyDict, PyList}};
use std::{fs, path::PathBuf};

pub fn load_range(
    py: Python<'_>,
    tier_dir: &PathBuf,
    prefix: &str,
    start_dt: DateTime<Utc>,
    end_dt: DateTime<Utc>,
) -> PyResult<Vec<Py<PyAny>>> {
    let native = l0_rust(py)?;
    let names: Vec<String> = fs::read_dir(tier_dir)
        .map_err(|err| PyValueError::new_err(err.to_string()))?
        .filter_map(Result::ok)
        .filter_map(|entry| entry.file_name().into_string().ok())
        .collect();
    let files = native
        .call_method1("service_research_range_files", (names, prefix, et_date(start_dt), et_date(end_dt)))?
        .downcast_into::<PyList>()?;
    let mut rows = Vec::new();
    for file in files.iter() {
        let path = tier_dir.join(file.extract::<String>()?);
        let out = native.call_method1("service_research_read_parquet_rows", (path.to_string_lossy().to_string(),))?;
        for row in out.downcast::<PyList>()?.iter() {
            let dict = row.downcast::<PyDict>()?;
            if let Some(ts) = dict.get_item("data_timestamp")?.and_then(|value| parse_ts_any(&value).ok().flatten()) {
                if ts >= start_dt && ts <= end_dt {
                    rows.push(row.unbind());
                }
            }
        }
    }
    Ok(rows)
}

pub fn load_latest(py: Python<'_>, tier_dir: &PathBuf, prefix: &str, count: usize) -> PyResult<Vec<Py<PyAny>>> {
    let native = l0_rust(py)?;
    let names: Vec<String> = fs::read_dir(tier_dir)
        .map_err(|err| PyValueError::new_err(err.to_string()))?
        .filter_map(Result::ok)
        .filter_map(|entry| entry.file_name().into_string().ok())
        .collect();
    let files = native.call_method1("service_research_latest_files", (names, prefix))?.downcast_into::<PyList>()?;
    let mut rows = Vec::new();
    for file in files.iter() {
        let path = tier_dir.join(file.extract::<String>()?);
        let out = native.call_method1("service_research_read_parquet_rows", (path.to_string_lossy().to_string(),))?;
        for row in out.downcast::<PyList>()?.iter() {
            rows.push(row.unbind());
        }
        if rows.len() >= count {
            break;
        }
    }
    rows.sort_by_key(|row| {
        row.bind(py)
            .downcast::<PyDict>()
            .ok()
            .and_then(|dict| dict.get_item("data_timestamp").ok().flatten())
            .and_then(|value| value.extract::<String>().ok())
            .unwrap_or_default()
    });
    Ok(rows)
}

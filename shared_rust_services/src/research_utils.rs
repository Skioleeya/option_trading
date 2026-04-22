use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyString};

fn parse_datetime<'py>(py: Python<'py>, raw: &Bound<'py, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    if raw.is_none() {
        return Ok(None);
    }
    let datetime_mod = py.import("datetime")?;
    let timezone = datetime_mod.getattr("timezone")?.getattr("utc")?;
    if raw.is_instance(&py.import("datetime")?.getattr("datetime")?)? {
        let dt = raw.call_method1("astimezone", (timezone,))?;
        return Ok(Some(dt.unbind()));
    }
    if let Ok(text) = raw.downcast::<PyString>() {
        let mut value = text.to_str()?.trim().to_string();
        if value.is_empty() {
            return Ok(None);
        }
        if value.ends_with('Z') {
            value = format!("{}+00:00", &value[..value.len() - 1]);
        }
        let dt_cls = datetime_mod.getattr("datetime")?;
        let parsed = dt_cls.call_method1("fromisoformat", (value,)).map_err(|_| {
            PyValueError::new_err("invalid ISO timestamp")
        })?;
        let normalized = if parsed.getattr("tzinfo")?.is_none() {
            let kwargs = PyDict::new(py);
            kwargs.set_item("tzinfo", timezone.clone())?;
            parsed.call_method("replace", (), Some(&kwargs))?
        } else {
            parsed.call_method1("astimezone", (timezone,))?
        };
        return Ok(Some(normalized.unbind()));
    }
    Ok(None)
}

#[pyfunction]
fn coerce_timestamp(py: Python<'_>, raw: &Bound<'_, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    parse_datetime(py, raw)
}

#[pyfunction]
fn extract_as_of_utc(
    py: Python<'_>,
    snapshot: &Bound<'_, PyAny>,
    payload: &Bound<'_, PyAny>,
    ts: &Bound<'_, PyAny>,
) -> PyResult<String> {
    if let Ok(extra) = snapshot.getattr("extra_metadata") {
        if let Ok(raw) = extra.get_item("source_data_timestamp_utc") {
            if let Some(dt) = parse_datetime(py, &raw)? {
                return dt.bind(py).call_method0("isoformat")?.extract();
            }
        }
    }
    if let Ok(payload_ts) = payload.getattr("data_timestamp") {
        if let Some(dt) = parse_datetime(py, &payload_ts)? {
            return dt.bind(py).call_method0("isoformat")?.extract();
        }
    }
    if let Some(dt) = parse_datetime(py, ts)? {
        return dt.bind(py).call_method0("isoformat")?.extract();
    }
    Err(PyValueError::new_err("timestamp coercion failed"))
}

#[pyfunction]
fn in_range(py: Python<'_>, ts: &Bound<'_, PyAny>, start_dt: &Bound<'_, PyAny>, end_dt: &Bound<'_, PyAny>) -> PyResult<bool> {
    let ts = match parse_datetime(py, ts)? {
        Some(value) => value,
        None => return Ok(false),
    };
    let start = parse_datetime(py, start_dt)?.ok_or_else(|| PyValueError::new_err("invalid start_dt"))?;
    let end = parse_datetime(py, end_dt)?.ok_or_else(|| PyValueError::new_err("invalid end_dt"))?;
    Ok(ts.bind(py).ge(start.bind(py))? && ts.bind(py).le(end.bind(py))?)
}

#[pyfunction]
fn coerce_dict(py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    if value.is_instance(&py.import("builtins")?.getattr("dict")?)? {
        Ok(value.clone().unbind())
    } else {
        Ok(pyo3::types::PyDict::new(py).unbind().into_any())
    }
}

#[pyfunction]
#[pyo3(signature = (value, default=None))]
fn to_float(value: &Bound<'_, PyAny>, default: Option<f64>) -> Option<f64> {
    value.extract::<f64>().ok().filter(|v| v.is_finite()).or(default)
}

#[pyfunction]
#[pyo3(signature = (value, default=0))]
fn coerce_int(value: &Bound<'_, PyAny>, default: i64) -> i64 {
    value.extract::<i64>().unwrap_or(default)
}

#[pyfunction]
fn safe_std(values: Vec<f64>) -> f64 {
    if values.len() < 2 {
        return 0.0;
    }
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    let variance = values.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / (values.len() - 1) as f64;
    variance.max(0.0).sqrt()
}

#[pyfunction(name = "f32")]
fn f32_value(value: &Bound<'_, PyAny>) -> Option<f64> {
    value.extract::<f64>().ok()
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(coerce_timestamp, m)?)?;
    m.add_function(wrap_pyfunction!(extract_as_of_utc, m)?)?;
    m.add_function(wrap_pyfunction!(in_range, m)?)?;
    m.add_function(wrap_pyfunction!(coerce_dict, m)?)?;
    m.add_function(wrap_pyfunction!(to_float, m)?)?;
    m.add_function(wrap_pyfunction!(coerce_int, m)?)?;
    m.add_function(wrap_pyfunction!(safe_std, m)?)?;
    m.add_function(wrap_pyfunction!(f32_value, m)?)?;
    Ok(())
}

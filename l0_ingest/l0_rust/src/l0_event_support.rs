use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};

fn mapping_or_attr<'py>(obj: &Bound<'py, PyAny>, key: &str) -> Option<Bound<'py, PyAny>> {
    if let Ok(value) = obj.call_method1("get", (key,)) {
        if !value.is_none() {
            return Some(value);
        }
    }
    obj.getattr(key).ok().filter(|value| !value.is_none())
}

fn safe_float(value: Option<Bound<'_, PyAny>>, default: f64) -> f64 {
    match value {
        Some(inner) => extract_float(&inner).unwrap_or(default),
        None => default,
    }
}

fn safe_int(value: Option<Bound<'_, PyAny>>, default: i64) -> i64 {
    if let Some(inner) = value {
        return extract_int(&inner).unwrap_or(default);
    }
    default
}

fn extract_float(value: &Bound<'_, PyAny>) -> Option<f64> {
    if let Ok(parsed) = value.extract::<Option<f64>>() {
        return parsed.filter(|num| num.is_finite());
    }
    if let Ok(text) = value.extract::<Option<String>>() {
        return text
            .and_then(|raw| raw.parse::<f64>().ok())
            .filter(|num| num.is_finite());
    }
    None
}

fn extract_int(value: &Bound<'_, PyAny>) -> Option<i64> {
    if let Ok(parsed) = value.extract::<Option<i64>>() {
        return parsed;
    }
    if let Some(parsed) = extract_float(value) {
        return Some(parsed as i64);
    }
    None
}

fn extract_event_type(raw_event: &Bound<'_, PyAny>) -> i64 {
    raw_event
        .getattr("event_type")
        .ok()
        .and_then(|value| extract_int(&value).or_else(|| value.getattr("value").ok().and_then(|inner| extract_int(&inner))))
        .unwrap_or(0)
}

fn direction_sign(raw_dir: &Bound<'_, PyAny>) -> i64 {
    if let Ok(value) = raw_dir.extract::<Option<i64>>() {
        match value.unwrap_or(0) {
            2 => return 1,
            1 => return -1,
            _ => {}
        }
    }
    if let Ok(text) = raw_dir.str() {
        let value = text.to_string();
        if value.contains("Up") || value == "2" {
            return 1;
        }
        if value.contains("Down") || value == "1" {
            return -1;
        }
    }
    0
}

#[pyfunction]
fn l0_event_extract_spy_spot_price(raw_event: Bound<'_, PyAny>) -> PyResult<Option<f64>> {
    let symbol = raw_event.getattr("symbol")?.extract::<String>()?;
    let event_type = extract_event_type(&raw_event);
    if symbol != "SPY.US" || event_type != 1 {
        return Ok(None);
    }
    let payload = raw_event.getattr("payload")?;
    let price = safe_float(mapping_or_attr(&payload, "last_done"), 0.0);
    Ok((price > 0.0).then_some(price))
}

#[pyfunction]
fn l0_event_normalize_trade_entry(py: Python<'_>, trade: Bound<'_, PyAny>) -> PyResult<Py<PyDict>> {
    let raw_dir = mapping_or_attr(&trade, "dir")
        .or_else(|| mapping_or_attr(&trade, "direction"))
        .unwrap_or_else(|| py.None().bind(py).clone());
    let dir_sign = direction_sign(&raw_dir);
    let out = PyDict::new(py);
    out.set_item("price", safe_float(mapping_or_attr(&trade, "price"), 0.0))?;
    let volume = safe_float(
        mapping_or_attr(&trade, "vol").or_else(|| mapping_or_attr(&trade, "volume")),
        0.0,
    );
    out.set_item("vol", volume)?;
    out.set_item("volume", volume)?;
    let timestamp = if let Some(ts) = mapping_or_attr(&trade, "timestamp") {
        if let Ok(value) = ts.getattr("timestamp") {
            value.call0()?.extract::<f64>().unwrap_or(0.0).floor() as i64
        } else {
            safe_int(Some(ts), 0)
        }
    } else {
        py.import("time")?.call_method0("time")?.extract::<f64>()?.floor() as i64
    };
    out.set_item("timestamp", timestamp)?;
    out.set_item("dir", dir_sign)?;
    out.set_item("direction", dir_sign)?;
    out.set_item("trade_type", safe_int(mapping_or_attr(&trade, "trade_type"), 0))?;
    Ok(out.unbind())
}

#[pyfunction]
fn l0_event_normalize_trade_entries(py: Python<'_>, trades: Bound<'_, PyAny>) -> PyResult<Py<PyList>> {
    let out = PyList::empty(py);
    for item in trades.try_iter()? {
        let trade = item?;
        out.append(l0_event_normalize_trade_entry(py, trade)?)?;
    }
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(l0_event_extract_spy_spot_price, module)?)?;
    module.add_function(wrap_pyfunction!(l0_event_normalize_trade_entry, module)?)?;
    module.add_function(wrap_pyfunction!(l0_event_normalize_trade_entries, module)?)?;
    Ok(())
}

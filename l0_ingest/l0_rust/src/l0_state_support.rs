use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyModule};

fn mapping_or_attr<'py>(obj: &Bound<'py, PyAny>, key: &str) -> Option<Bound<'py, PyAny>> {
    if let Ok(value) = obj.call_method1("get", (key,)) {
        if !value.is_none() {
            return Some(value);
        }
    }
    obj.getattr(key).ok().filter(|value| !value.is_none())
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
    extract_float(value).map(|num| num as i64)
}

fn is_positive_numeric(value: Option<Bound<'_, PyAny>>) -> bool {
    value
        .and_then(|inner| extract_float(&inner))
        .map(|num| num > 0.0)
        .unwrap_or(false)
}

fn copy_dict<'py>(py: Python<'py>, source: &Bound<'py, PyDict>) -> PyResult<Bound<'py, PyDict>> {
    let out = PyDict::new(py);
    for (key, value) in source.iter() {
        out.set_item(key, value)?;
    }
    Ok(out)
}

fn set_if_changed(entry: &Bound<'_, PyDict>, key: &str, value: &Bound<'_, PyAny>, changed: &mut bool) -> PyResult<()> {
    if value.is_none() {
        return Ok(());
    }
    let current = entry.get_item(key)?;
    let equal = current
        .as_ref()
        .and_then(|inner| inner.eq(value).ok())
        .unwrap_or(false);
    if !equal {
        entry.set_item(key, value)?;
        *changed = true;
    }
    Ok(())
}

#[pyfunction]
fn l0_state_default_entry(
    py: Python<'_>,
    symbol: String,
    strike: f64,
    opt_type: String,
) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("symbol", symbol)?;
    out.set_item("strike", strike)?;
    out.set_item("type", opt_type)?;
    out.set_item("bid", 0.0_f64)?;
    out.set_item("ask", 0.0_f64)?;
    out.set_item("last_price", 0.0_f64)?;
    out.set_item("volume", 0_i64)?;
    out.set_item("open_interest", 0_i64)?;
    out.set_item("implied_volatility", 0.0_f64)?;
    out.set_item("iv_timestamp", 0.0_f64)?;
    out.set_item("delta", 0.0_f64)?;
    out.set_item("gamma", 0.0_f64)?;
    out.set_item("theta", 0.0_f64)?;
    out.set_item("vega", 0.0_f64)?;
    out.set_item("current_volume", 0.0_f64)?;
    out.set_item("turnover", 0.0_f64)?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (entry, event, is_rest, ws_price_seen, ws_volume_seen, ws_current_volume_seen, ws_turnover_seen, max_ws_flow_volume))]
fn l0_state_apply_quote(
    py: Python<'_>,
    entry: Bound<'_, PyDict>,
    event: Bound<'_, PyAny>,
    is_rest: bool,
    ws_price_seen: bool,
    ws_volume_seen: bool,
    ws_current_volume_seen: bool,
    ws_turnover_seen: bool,
    max_ws_flow_volume: f64,
) -> PyResult<Py<PyDict>> {
    let next_entry = copy_dict(py, &entry)?;
    let mut changed = false;
    let bid = mapping_or_attr(&event, "bid");
    let ask = mapping_or_attr(&event, "ask");
    let last_price = mapping_or_attr(&event, "last_price");
    let volume = mapping_or_attr(&event, "volume");
    let current_volume = mapping_or_attr(&event, "current_volume");
    let turnover = mapping_or_attr(&event, "turnover");
    let event_type = mapping_or_attr(&event, "event_type")
        .and_then(|raw| extract_int(&raw).or_else(|| raw.getattr("value").ok().and_then(|inner| extract_int(&inner))))
        .unwrap_or(0);

    let mut next_ws_price_seen = ws_price_seen;
    let mut next_ws_volume_seen = ws_volume_seen;
    let mut next_ws_current_volume_seen = ws_current_volume_seen;
    let mut next_ws_turnover_seen = ws_turnover_seen;
    let mut ws_volume_dropped_inc = 0_i64;
    let mut ws_current_volume_dropped_inc = 0_i64;
    let mut ws_volume_drop_value: Option<f64> = None;
    let mut ws_current_volume_drop_value: Option<f64> = None;

    if !is_rest {
        if is_positive_numeric(bid.clone()) || is_positive_numeric(ask.clone()) || is_positive_numeric(last_price.clone()) {
            next_ws_price_seen = true;
        }
        for (field, value) in [("bid", bid.clone()), ("ask", ask.clone()), ("last_price", last_price.clone())] {
            if is_positive_numeric(value.clone()) {
                if let Some(inner) = value {
                    set_if_changed(&next_entry, field, &inner, &mut changed)?;
                }
            }
        }

        let raw_volume = volume.as_ref().and_then(extract_float);
        let raw_current_volume = current_volume.as_ref().and_then(extract_float);
        let sanitized_volume = raw_volume.filter(|num| *num > 0.0 && *num <= max_ws_flow_volume);
        let sanitized_current_volume = raw_current_volume.filter(|num| *num > 0.0 && *num <= max_ws_flow_volume);
        if raw_volume.filter(|num| *num > 0.0).is_some() && sanitized_volume.is_none() {
            ws_volume_dropped_inc = 1;
            ws_volume_drop_value = raw_volume;
        }
        if raw_current_volume.filter(|num| *num > 0.0).is_some() && sanitized_current_volume.is_none() {
            ws_current_volume_dropped_inc = 1;
            ws_current_volume_drop_value = raw_current_volume;
        }

        if event_type == 1 || event_type == 3 {
            let turnover_positive = turnover.as_ref().and_then(extract_float).map(|num| num > 0.0).unwrap_or(false);
            let volume_owned_by_ws = event_type == 3 || turnover_positive;
            let ws_volume = match (sanitized_volume, sanitized_current_volume) {
                (Some(left), Some(right)) => left.min(right),
                (Some(left), None) => left,
                (None, Some(right)) => right,
                (None, None) => 0.0,
            };
            if volume_owned_by_ws && ws_volume > 0.0 {
                next_entry.set_item("volume", ws_volume)?;
                changed = true;
                next_ws_volume_seen = true;
            }
            if let Some(value) = sanitized_current_volume {
                next_entry.set_item("current_volume", value)?;
                changed = true;
                next_ws_current_volume_seen = true;
            }
            if let Some(value) = turnover {
                set_if_changed(&next_entry, "turnover", &value, &mut changed)?;
                if turnover_positive {
                    next_ws_turnover_seen = true;
                }
            }
        }
    } else {
        if !ws_price_seen {
            for (field, value) in [("bid", bid), ("ask", ask), ("last_price", last_price)] {
                if let Some(inner) = value {
                    set_if_changed(&next_entry, field, &inner, &mut changed)?;
                }
            }
        }
        if !ws_volume_seen {
            if let Some(value) = volume {
                set_if_changed(&next_entry, "volume", &value, &mut changed)?;
            }
        }
        if !ws_current_volume_seen {
            if let Some(value) = current_volume {
                set_if_changed(&next_entry, "current_volume", &value, &mut changed)?;
            }
        }
        if !ws_turnover_seen {
            if let Some(value) = turnover {
                set_if_changed(&next_entry, "turnover", &value, &mut changed)?;
            }
        }
    }

    for field in [
        "implied_volatility",
        "iv_timestamp",
        "delta",
        "gamma",
        "theta",
        "vega",
    ] {
        if let Some(value) = mapping_or_attr(&event, field) {
            set_if_changed(&next_entry, field, &value, &mut changed)?;
        }
    }

    let out = PyDict::new(py);
    out.set_item("entry", next_entry)?;
    out.set_item("changed", changed)?;
    out.set_item("ws_price_seen", next_ws_price_seen)?;
    out.set_item("ws_volume_seen", next_ws_volume_seen)?;
    out.set_item("ws_current_volume_seen", next_ws_current_volume_seen)?;
    out.set_item("ws_turnover_seen", next_ws_turnover_seen)?;
    out.set_item("ws_volume_dropped_inc", ws_volume_dropped_inc)?;
    out.set_item("ws_current_volume_dropped_inc", ws_current_volume_dropped_inc)?;
    out.set_item("ws_volume_drop_value", ws_volume_drop_value)?;
    out.set_item("ws_current_volume_drop_value", ws_current_volume_drop_value)?;
    Ok(out.unbind())
}

#[pyfunction]
fn l0_state_apply_depth(
    py: Python<'_>,
    entry: Bound<'_, PyDict>,
    event: Bound<'_, PyAny>,
) -> PyResult<Py<PyDict>> {
    let next_entry = copy_dict(py, &entry)?;
    let mut changed = false;
    for field in ["bid", "ask"] {
        if let Some(value) = mapping_or_attr(&event, field) {
            if is_positive_numeric(Some(value.clone())) {
                set_if_changed(&next_entry, field, &value, &mut changed)?;
            }
        }
    }
    let out = PyDict::new(py);
    out.set_item("entry", next_entry)?;
    out.set_item("changed", changed)?;
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(l0_state_default_entry, module)?)?;
    module.add_function(wrap_pyfunction!(l0_state_apply_quote, module)?)?;
    module.add_function(wrap_pyfunction!(l0_state_apply_depth, module)?)?;
    Ok(())
}

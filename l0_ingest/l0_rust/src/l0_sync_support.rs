use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};

const MAX_WARM_UP_SUBSCRIPTION_CAP: i64 = 500;
const MIN_BATCH_SIZE: i64 = 1;
const MAX_BATCH_SIZE: i64 = 50;
const PRICE_REPAIR_BATCH_LIMIT: usize = 4;
const PRICE_REPAIR_COOLDOWN_SECONDS: f64 = 15.0;

fn attr_or_item<'py>(obj: &Bound<'py, PyAny>, name: &str) -> Option<Bound<'py, PyAny>> {
    if let Ok(value) = obj.call_method1("get", (name,)) {
        if !value.is_none() {
            return Some(value);
        }
    }
    obj.getattr(name).ok().filter(|value| !value.is_none())
}

fn as_float(value: Bound<'_, PyAny>) -> Option<f64> {
    if let Ok(parsed) = value.extract::<f64>() {
        return parsed.is_finite().then_some(parsed);
    }
    if let Ok(raw) = value.extract::<String>() {
        return raw.parse::<f64>().ok().filter(|num| num.is_finite());
    }
    None
}

fn as_int(value: Bound<'_, PyAny>) -> Option<i64> {
    if let Ok(parsed) = value.extract::<i64>() {
        return Some(parsed);
    }
    as_float(value).map(|num| num as i64)
}

#[pyfunction]
#[pyo3(signature = (raw_cap=None))]
fn l0_sync_clamp_subscription_cap(raw_cap: Option<i64>) -> i64 {
    raw_cap
        .unwrap_or(MAX_WARM_UP_SUBSCRIPTION_CAP)
        .max(MIN_BATCH_SIZE)
        .min(MAX_WARM_UP_SUBSCRIPTION_CAP)
}

#[pyfunction]
#[pyo3(signature = (max_symbol_weight=None))]
fn l0_sync_safe_batch_size(max_symbol_weight: Option<i64>) -> i64 {
    max_symbol_weight
        .unwrap_or(MAX_BATCH_SIZE)
        .max(MIN_BATCH_SIZE)
        .min(MAX_BATCH_SIZE)
}

#[pyfunction]
fn l0_sync_split_sync_chunks(py: Python<'_>, symbols: Vec<String>) -> PyResult<Py<PyList>> {
    let out = PyList::empty(py);
    if symbols.is_empty() {
        return Ok(out.unbind());
    }
    let half = symbols.len() / 2;
    out.append(symbols[..half].to_vec())?;
    out.append(symbols[half..].to_vec())?;
    Ok(out.unbind())
}

#[pyfunction]
fn l0_sync_parse_implied_volatility(item: Bound<'_, PyAny>) -> Option<f64> {
    if let Some(value) = attr_or_item(&item, "implied_volatility_decimal").and_then(as_float) {
        return Some(value);
    }
    let parsed = attr_or_item(&item, "implied_volatility").and_then(as_float)?;
    Some(if parsed > 1.0 { parsed / 100.0 } else { parsed })
}

#[pyfunction]
fn l0_sync_parse_open_interest(item: Bound<'_, PyAny>) -> Option<i64> {
    attr_or_item(&item, "open_interest").and_then(as_int)
}

#[pyfunction]
fn l0_sync_is_rate_limit_error(message: String) -> bool {
    message.contains("301607")
}

#[pyfunction]
fn l0_sync_pick_price_repair_candidates(
    py: Python<'_>,
    batch: Vec<String>,
    eligible_symbols: Vec<String>,
    last_repair_at: Bound<'_, PyDict>,
    now_mono: f64,
) -> PyResult<Py<PyList>> {
    let eligible = eligible_symbols.into_iter().collect::<std::collections::HashSet<_>>();
    let out = PyList::empty(py);
    for symbol in batch {
        if !eligible.contains(&symbol) {
            continue;
        }
        let last_ts = last_repair_at
            .get_item(&symbol)?
            .and_then(as_float)
            .unwrap_or(0.0);
        if (now_mono - last_ts) < PRICE_REPAIR_COOLDOWN_SECONDS {
            continue;
        }
        out.append(symbol)?;
        if out.len() >= PRICE_REPAIR_BATCH_LIMIT {
            break;
        }
    }
    Ok(out.unbind())
}

#[pyfunction]
fn l0_sync_apply_repair_rows(
    py: Python<'_>,
    rows: Bound<'_, PyAny>,
    now_mono: f64,
) -> PyResult<Py<PyDict>> {
    let stats = PyDict::new(py);
    let updates = PyList::empty(py);
    let last_repair_at = PyDict::new(py);
    let mut updated = 0_i64;
    for item in rows.try_iter()? {
        let row = item?;
        let symbol = attr_or_item(&row, "symbol")
            .and_then(|value| value.extract::<String>().ok())
            .unwrap_or_default();
        if symbol.is_empty() {
            continue;
        }
        let update = PyDict::new(py);
        update.set_item("symbol", &symbol)?;
        update.set_item("item", row)?;
        updates.append(update)?;
        last_repair_at.set_item(symbol, now_mono)?;
        updated += 1;
    }
    stats.set_item("updated", updated)?;
    stats.set_item("updates", updates)?;
    stats.set_item("last_repair_at", last_repair_at)?;
    Ok(stats.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(l0_sync_clamp_subscription_cap, module)?)?;
    module.add_function(wrap_pyfunction!(l0_sync_safe_batch_size, module)?)?;
    module.add_function(wrap_pyfunction!(l0_sync_split_sync_chunks, module)?)?;
    module.add_function(wrap_pyfunction!(l0_sync_parse_implied_volatility, module)?)?;
    module.add_function(wrap_pyfunction!(l0_sync_parse_open_interest, module)?)?;
    module.add_function(wrap_pyfunction!(l0_sync_is_rate_limit_error, module)?)?;
    module.add_function(wrap_pyfunction!(l0_sync_pick_price_repair_candidates, module)?)?;
    module.add_function(wrap_pyfunction!(l0_sync_apply_repair_rows, module)?)?;
    Ok(())
}

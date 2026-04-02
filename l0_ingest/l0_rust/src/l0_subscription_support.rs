use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};
use std::collections::{HashMap, HashSet};

const CALL_WINDOW: f64 = 25.0;
const PUT_WINDOW: f64 = 35.0;
const LONGPORT_MAX_SUBSCRIPTIONS: i64 = 500;

fn attr_or_item<'py>(obj: &Bound<'py, PyAny>, name: &str) -> Option<Bound<'py, PyAny>> {
    if let Ok(value) = obj.call_method1("get", (name,)) {
        if !value.is_none() {
            return Some(value);
        }
    }
    obj.getattr(name).ok().filter(|value| !value.is_none())
}

fn as_text(value: Option<Bound<'_, PyAny>>) -> Option<String> {
    value.and_then(|inner| inner.extract::<String>().ok())
}

fn as_float(value: Option<Bound<'_, PyAny>>) -> Option<f64> {
    let inner = value?;
    if let Ok(parsed) = inner.extract::<f64>() {
        return parsed.is_finite().then_some(parsed);
    }
    if let Ok(raw) = inner.extract::<String>() {
        return raw.parse::<f64>().ok().filter(|num| num.is_finite());
    }
    None
}

fn parse_symbol_expiry(symbol: &str) -> i64 {
    let bytes = symbol.as_bytes();
    let mut idx = 0usize;
    while idx < bytes.len() {
        if !bytes[idx].is_ascii_uppercase() {
            idx += 1;
            continue;
        }
        let start = idx;
        while idx < bytes.len() && bytes[idx].is_ascii_uppercase() {
            idx += 1;
        }
        if start == 0 && idx + 7 <= bytes.len() {
            let digits = &symbol[idx..idx + 6];
            let cp = bytes[idx + 6];
            if digits.bytes().all(|byte| byte.is_ascii_digit()) && matches!(cp, b'C' | b'P') {
                return digits.parse::<i64>().unwrap_or(999_999);
            }
        }
    }
    999_999
}

fn symbol_priority_key(
    symbol: &str,
    spot: Option<f64>,
    strike_map: &HashMap<String, f64>,
) -> (i64, f64, String) {
    let expiry_date = parse_symbol_expiry(symbol);
    let distance = match (spot, strike_map.get(symbol)) {
        (Some(spot_value), Some(strike)) => (strike - spot_value).abs(),
        _ => f64::INFINITY,
    };
    (expiry_date, distance, symbol.to_string())
}

#[pyfunction]
fn l0_subscription_clamp_cap(configured_cap: i64) -> i64 {
    configured_cap.max(1).min(LONGPORT_MAX_SUBSCRIPTIONS)
}

#[pyfunction]
fn l0_subscription_collect_targets(
    py: Python<'_>,
    rows: Bound<'_, PyAny>,
    spot: f64,
) -> PyResult<Py<PyDict>> {
    let targets = PyList::empty(py);
    let strike_map = PyDict::new(py);
    let mut seen = HashSet::new();
    for item in rows.try_iter()? {
        let row = item?;
        let strike = as_float(attr_or_item(&row, "price")).unwrap_or(0.0);
        let dist = strike - spot;
        if dist > CALL_WINDOW || dist < -PUT_WINDOW {
            continue;
        }
        if let Some(call_symbol) = as_text(attr_or_item(&row, "call_symbol")) {
            if seen.insert(call_symbol.clone()) {
                targets.append(&call_symbol)?;
            }
            strike_map.set_item(call_symbol, strike)?;
        }
        if let Some(put_symbol) = as_text(attr_or_item(&row, "put_symbol")) {
            if seen.insert(put_symbol.clone()) {
                targets.append(&put_symbol)?;
            }
            strike_map.set_item(put_symbol, strike)?;
        }
    }
    let out = PyDict::new(py);
    out.set_item("targets", targets)?;
    out.set_item("symbol_to_strike", strike_map)?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (target_symbols, mandatory_symbols, subscription_cap, symbol_to_strike, spot=None))]
fn l0_subscription_enforce_cap(
    py: Python<'_>,
    target_symbols: Vec<String>,
    mandatory_symbols: Vec<String>,
    subscription_cap: usize,
    symbol_to_strike: Bound<'_, PyDict>,
    spot: Option<f64>,
) -> PyResult<Py<PyDict>> {
    let mut strike_map = HashMap::new();
    for (key, value) in symbol_to_strike.iter() {
        if let (Ok(symbol), Ok(strike)) = (key.extract::<String>(), value.extract::<f64>()) {
            strike_map.insert(symbol, strike);
        }
    }
    let mut mandatory: Vec<String> = mandatory_symbols;
    if mandatory.len() > subscription_cap {
        mandatory.sort_by(|left, right| {
            symbol_priority_key(left, spot, &strike_map)
                .partial_cmp(&symbol_priority_key(right, spot, &strike_map))
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        mandatory.truncate(subscription_cap);
    }

    let mut kept = mandatory.iter().cloned().collect::<HashSet<_>>();
    let remaining = subscription_cap.saturating_sub(kept.len());
    if remaining > 0 {
        let mut candidates = target_symbols
            .into_iter()
            .filter(|symbol| !kept.contains(symbol))
            .collect::<Vec<_>>();
        candidates.sort_by(|left, right| {
            symbol_priority_key(left, spot, &strike_map)
                .partial_cmp(&symbol_priority_key(right, spot, &strike_map))
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        for symbol in candidates.into_iter().take(remaining) {
            kept.insert(symbol);
        }
    }

    let kept_list = PyList::empty(py);
    for symbol in &kept {
        kept_list.append(symbol)?;
    }
    let filtered = PyDict::new(py);
    for symbol in &kept {
        if let Some(strike) = strike_map.get(symbol) {
            filtered.set_item(symbol, strike)?;
        }
    }
    let out = PyDict::new(py);
    out.set_item("kept", kept_list)?;
    out.set_item("symbol_to_strike", filtered)?;
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(l0_subscription_clamp_cap, module)?)?;
    module.add_function(wrap_pyfunction!(l0_subscription_collect_targets, module)?)?;
    module.add_function(wrap_pyfunction!(l0_subscription_enforce_cap, module)?)?;
    Ok(())
}

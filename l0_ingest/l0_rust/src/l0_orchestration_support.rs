use pyo3::prelude::*;
use pyo3::types::{PyAny, PyModule};

const U64_BYTE_WIDTH: usize = 8;

fn attr_or_item<'py>(obj: &Bound<'py, PyAny>, name: &str) -> Option<Bound<'py, PyAny>> {
    if let Ok(value) = obj.call_method1("get", (name,)) {
        if !value.is_none() {
            return Some(value);
        }
    }
    obj.getattr(name).ok().filter(|value| !value.is_none())
}

fn positive_float(value: Bound<'_, PyAny>) -> Option<f64> {
    if let Ok(parsed) = value.extract::<f64>() {
        return (parsed.is_finite() && parsed > 0.0).then_some(parsed);
    }
    if let Ok(raw) = value.extract::<String>() {
        return raw
            .parse::<f64>()
            .ok()
            .filter(|parsed| parsed.is_finite() && *parsed > 0.0);
    }
    None
}

fn parse_symbol_expiry(symbol: &str) -> Option<(usize, usize)> {
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
                return Some((idx, idx + 6));
            }
        }
    }
    None
}

#[pyfunction]
fn l0_orch_infer_strike_from_symbol(symbol: String) -> Option<f64> {
    let normalized = symbol.trim().to_ascii_uppercase();
    let (_, end) = parse_symbol_expiry(&normalized)?;
    let strike_digits = normalized.get(end + 1..normalized.len())?;
    let strike_digits = strike_digits
        .split('.')
        .next()
        .filter(|value| !value.is_empty())?;
    let raw = strike_digits.parse::<i64>().ok()?;
    let strike = raw as f64 / 1000.0;
    (strike > 0.0).then_some(strike)
}

#[pyfunction]
fn l0_orch_read_u64(buffer: Vec<u8>, ptr: usize) -> u64 {
    if buffer.len() < ptr + U64_BYTE_WIDTH {
        return 0;
    }
    let bytes = &buffer[ptr..ptr + U64_BYTE_WIDTH];
    u64::from_le_bytes(bytes.try_into().unwrap_or([0u8; U64_BYTE_WIDTH]))
}

#[pyfunction]
fn l0_orch_next_trading_day_iso(base_day_iso: String) -> PyResult<String> {
    let format = time::macros::format_description!("[year]-[month]-[day]");
    let base_day = time::Date::parse(&base_day_iso, &format)
        .map_err(|err| pyo3::exceptions::PyValueError::new_err(format!("invalid date: {err}")))?;
    let mut probe = base_day
        .next_day()
        .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("next trading day overflow"))?;
    while matches!(probe.weekday(), time::Weekday::Saturday | time::Weekday::Sunday) {
        probe = probe
            .next_day()
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("next trading day overflow"))?;
    }
    probe
        .format(&format)
        .map_err(|err| pyo3::exceptions::PyValueError::new_err(format!("date format failed: {err}")))
}

#[pyfunction]
fn l0_orch_to_positive_float(raw: Bound<'_, PyAny>) -> Option<f64> {
    positive_float(raw)
}

#[pyfunction]
fn l0_orch_normalize_decimal_ratio(raw: Bound<'_, PyAny>) -> Option<f64> {
    let mut value = positive_float(raw)?;
    if value > 1.0 {
        value /= 100.0;
    }
    (value > 0.0 && value <= 5.0).then_some(value)
}

#[pyfunction]
fn l0_orch_average_valid(values: Vec<Option<f64>>) -> Option<f64> {
    let valid = values
        .into_iter()
        .flatten()
        .filter(|value| *value > 0.0)
        .collect::<Vec<_>>();
    if valid.is_empty() {
        return None;
    }
    Some(valid.iter().sum::<f64>() / valid.len() as f64)
}

#[pyfunction]
fn l0_orch_select_nearest_chain_index(rows: Bound<'_, PyAny>, spot: f64) -> PyResult<Option<usize>> {
    let mut best_index = None;
    let mut best_distance = f64::INFINITY;
    for (idx, item) in rows.try_iter()?.enumerate() {
        let row = item?;
        let strike = attr_or_item(&row, "strike_price")
            .or_else(|| attr_or_item(&row, "price"))
            .and_then(positive_float);
        let Some(value) = strike else {
            continue;
        };
        let distance = (value - spot).abs();
        if distance < best_distance {
            best_distance = distance;
            best_index = Some(idx);
        }
    }
    Ok(best_index)
}

#[pyfunction]
fn l0_orch_extract_option_iv_decimal(quote: Bound<'_, PyAny>) -> Option<f64> {
    if let Some(primary) = attr_or_item(&quote, "implied_volatility_decimal") {
        return l0_orch_normalize_decimal_ratio(primary);
    }
    attr_or_item(&quote, "implied_volatility").and_then(l0_orch_normalize_decimal_ratio)
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(l0_orch_infer_strike_from_symbol, module)?)?;
    module.add_function(wrap_pyfunction!(l0_orch_read_u64, module)?)?;
    module.add_function(wrap_pyfunction!(l0_orch_next_trading_day_iso, module)?)?;
    module.add_function(wrap_pyfunction!(l0_orch_to_positive_float, module)?)?;
    module.add_function(wrap_pyfunction!(l0_orch_normalize_decimal_ratio, module)?)?;
    module.add_function(wrap_pyfunction!(l0_orch_average_valid, module)?)?;
    module.add_function(wrap_pyfunction!(l0_orch_select_nearest_chain_index, module)?)?;
    module.add_function(wrap_pyfunction!(l0_orch_extract_option_iv_decimal, module)?)?;
    Ok(())
}

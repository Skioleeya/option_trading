use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};

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

fn parse_iv(row: &Bound<'_, PyAny>) -> f64 {
    if let Some(value) = attr_or_item(row, "implied_volatility_decimal").and_then(as_float) {
        return value;
    }
    let parsed = attr_or_item(row, "implied_volatility").and_then(as_float);
    match parsed {
        Some(value) if value > 1.0 => value / 100.0,
        Some(value) => value,
        None => 0.0,
    }
}

fn parse_option_type(symbol: &str) -> &'static str {
    if symbol.contains('C') { "CALL" } else { "PUT" }
}

#[pyfunction]
fn l0_poller_build_symbol_metadata(
    py: Python<'_>,
    chain_info: Bound<'_, PyAny>,
    spot: f64,
    window: f64,
) -> PyResult<Py<PyDict>> {
    let data = PyDict::new(py);
    let sym_to_strike = PyDict::new(py);
    let standard_by_symbol = PyDict::new(py);
    let mut kept = 0_i64;
    for item in chain_info.try_iter()? {
        let row = item?;
        let strike = attr_or_item(&row, "price").and_then(as_float).unwrap_or(0.0);
        if (strike - spot).abs() > window {
            continue;
        }
        let standard = attr_or_item(&row, "standard")
            .and_then(|value| value.extract::<bool>().ok())
            .unwrap_or(false);
        if let Some(symbol) = attr_or_item(&row, "call_symbol").and_then(|value| value.extract::<String>().ok()) {
            if !symbol.is_empty() {
                sym_to_strike.set_item(&symbol, strike)?;
                standard_by_symbol.set_item(&symbol, standard)?;
                kept += 1;
            }
        }
        if let Some(symbol) = attr_or_item(&row, "put_symbol").and_then(|value| value.extract::<String>().ok()) {
            if !symbol.is_empty() {
                sym_to_strike.set_item(&symbol, strike)?;
                standard_by_symbol.set_item(&symbol, standard)?;
                kept += 1;
            }
        }
    }
    data.set_item("sym_to_strike", sym_to_strike)?;
    data.set_item("standard_by_symbol", standard_by_symbol)?;
    data.set_item("kept", kept)?;
    Ok(data.unbind())
}

#[pyfunction]
fn l0_poller_normalize_calc_rows(
    py: Python<'_>,
    results: Bound<'_, PyAny>,
    expiry: String,
    tier: String,
    sym_to_strike: Bound<'_, PyDict>,
    standard_by_symbol: Bound<'_, PyDict>,
) -> PyResult<Py<PyList>> {
    let rows = PyList::empty(py);
    for item in results.try_iter()? {
        let row = item?;
        let symbol = attr_or_item(&row, "symbol")
            .and_then(|value| value.extract::<String>().ok())
            .unwrap_or_default();
        if symbol.is_empty() {
            continue;
        }
        let strike = sym_to_strike
            .get_item(&symbol)?
            .and_then(as_float)
            .unwrap_or(0.0);
        let volume = attr_or_item(&row, "volume").and_then(as_int).unwrap_or(0);
        let open_interest = attr_or_item(&row, "open_interest").and_then(as_int).unwrap_or(0);
        let premium = attr_or_item(&row, "premium").and_then(as_float).unwrap_or(0.0);
        let standard = standard_by_symbol
            .get_item(&symbol)?
            .and_then(|value| value.extract::<bool>().ok())
            .unwrap_or(false);
        let payload = PyDict::new(py);
        payload.set_item("symbol", &symbol)?;
        payload.set_item("strike", strike)?;
        payload.set_item("type", parse_option_type(&symbol))?;
        payload.set_item("expiry", &expiry)?;
        payload.set_item("tier", &tier)?;
        payload.set_item("volume", volume)?;
        payload.set_item("open_interest", open_interest)?;
        payload.set_item("implied_volatility", parse_iv(&row))?;
        payload.set_item("premium", premium)?;
        payload.set_item("standard", standard)?;
        rows.append(payload)?;
    }
    Ok(rows.unbind())
}

#[pyfunction]
fn l0_poller_top_open_interest(
    py: Python<'_>,
    rows: Bound<'_, PyAny>,
    limit: usize,
) -> PyResult<Py<PyList>> {
    let mut ranked = Vec::<(i64, Py<PyAny>)>::new();
    for item in rows.try_iter()? {
        let row = item?;
        let open_interest = attr_or_item(&row, "open_interest").and_then(as_int).unwrap_or(0);
        ranked.push((open_interest, row.unbind()));
    }
    ranked.sort_by(|left, right| right.0.cmp(&left.0));
    let out = PyList::empty(py);
    for (_, row) in ranked.into_iter().take(limit) {
        out.append(row)?;
    }
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(l0_poller_build_symbol_metadata, module)?)?;
    module.add_function(wrap_pyfunction!(l0_poller_normalize_calc_rows, module)?)?;
    module.add_function(wrap_pyfunction!(l0_poller_top_open_interest, module)?)?;
    Ok(())
}

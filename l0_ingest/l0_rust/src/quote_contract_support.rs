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

fn as_text(value: Option<Bound<'_, PyAny>>) -> Option<String> {
    value.and_then(|inner| {
        let text = inner.str().ok()?.to_string();
        let trimmed = text.trim().to_string();
        (!trimmed.is_empty()).then_some(trimmed)
    })
}

fn as_float(value: Option<Bound<'_, PyAny>>) -> Option<f64> {
    let inner = value?;
    if let Ok(parsed) = inner.extract::<Option<f64>>() {
        return parsed.filter(|num| num.is_finite());
    }
    if let Ok(text) = inner.extract::<Option<String>>() {
        return text
            .and_then(|raw| raw.parse::<f64>().ok())
            .filter(|num| num.is_finite());
    }
    None
}

fn as_int(value: Option<Bound<'_, PyAny>>) -> Option<i64> {
    let inner = value?;
    if let Ok(parsed) = inner.extract::<Option<i64>>() {
        return parsed;
    }
    as_float(Some(inner)).map(|num| num as i64)
}

fn to_trade_status(value: Option<Bound<'_, PyAny>>) -> Option<i64> {
    if let Some(code) = as_int(value.clone()) {
        return Some(code);
    }
    let enum_value = value.and_then(|inner| mapping_or_attr(&inner, "value"));
    as_int(enum_value)
}

fn float_from_text(raw: Option<String>) -> Option<f64> {
    let parsed = raw.and_then(|value| value.parse::<f64>().ok())?;
    parsed.is_finite().then_some(parsed)
}

fn to_decimal_ratio(raw: Option<String>) -> Option<f64> {
    let parsed = float_from_text(raw)?;
    if parsed < 0.0 {
        return None;
    }
    Some(if parsed > 1.0 { parsed / 100.0 } else { parsed })
}

fn to_iso_date(raw: Option<String>) -> Option<String> {
    let value = raw?;
    let digits: String = value.chars().filter(|ch| ch.is_ascii_digit()).collect();
    match digits.len() {
        8 => Some(format!("{}-{}-{}", &digits[0..4], &digits[4..6], &digits[6..8])),
        6 => Some(format!("20{}-{}-{}", &digits[0..2], &digits[2..4], &digits[4..6])),
        _ => None,
    }
}

#[pyfunction]
fn quote_api_build_option_quote_contract(py: Python<'_>, row: Bound<'_, PyAny>) -> PyResult<Py<PyDict>> {
    let option_extend_src = mapping_or_attr(&row, "option_extend");
    let implied_raw = as_text(option_extend_src.as_ref().and_then(|src| mapping_or_attr(src, "implied_volatility")))
        .or_else(|| as_text(mapping_or_attr(&row, "implied_volatility_raw")))
        .or_else(|| as_text(mapping_or_attr(&row, "implied_volatility")));
    let hist_raw = as_text(option_extend_src.as_ref().and_then(|src| mapping_or_attr(src, "historical_volatility")))
        .or_else(|| as_text(mapping_or_attr(&row, "historical_volatility_raw")))
        .or_else(|| as_text(mapping_or_attr(&row, "historical_volatility")));
    let expiry_raw = as_text(option_extend_src.as_ref().and_then(|src| mapping_or_attr(src, "expiry_date")))
        .or_else(|| as_text(mapping_or_attr(&row, "expiry_date_raw")))
        .or_else(|| as_text(mapping_or_attr(&row, "expiry_date")));
    let strike_raw = as_text(option_extend_src.as_ref().and_then(|src| mapping_or_attr(src, "strike_price")))
        .or_else(|| as_text(mapping_or_attr(&row, "strike_price_raw")))
        .or_else(|| as_text(mapping_or_attr(&row, "strike_price")));
    let multiplier_raw = as_text(option_extend_src.as_ref().and_then(|src| mapping_or_attr(src, "contract_multiplier")))
        .or_else(|| as_text(mapping_or_attr(&row, "contract_multiplier")));
    let size_raw = as_text(option_extend_src.as_ref().and_then(|src| mapping_or_attr(src, "contract_size")))
        .or_else(|| as_text(mapping_or_attr(&row, "contract_size")));
    let mut open_interest = as_int(mapping_or_attr(&row, "open_interest"));
    if open_interest.is_none() {
        open_interest = option_extend_src.as_ref().and_then(|src| as_int(mapping_or_attr(src, "open_interest")));
    }

    let option_extend = PyDict::new(py);
    let extend_has_values =
        implied_raw.is_some()
        || open_interest.is_some()
        || expiry_raw.is_some()
        || strike_raw.is_some()
        || multiplier_raw.is_some()
        || option_extend_src.as_ref().and_then(|src| as_text(mapping_or_attr(src, "contract_type"))).is_some()
        || size_raw.is_some()
        || option_extend_src.as_ref().and_then(|src| as_text(mapping_or_attr(src, "direction"))).is_some()
        || hist_raw.is_some()
        || option_extend_src.as_ref().and_then(|src| as_text(mapping_or_attr(src, "underlying_symbol"))).is_some();

    if extend_has_values {
        option_extend.set_item("implied_volatility", implied_raw.clone())?;
        option_extend.set_item("open_interest", open_interest)?;
        option_extend.set_item("expiry_date", expiry_raw.clone())?;
        option_extend.set_item("strike_price", strike_raw.clone())?;
        option_extend.set_item("contract_multiplier", multiplier_raw.clone())?;
        option_extend.set_item(
            "contract_type",
            option_extend_src.as_ref().and_then(|src| as_text(mapping_or_attr(src, "contract_type")))
                .or_else(|| as_text(mapping_or_attr(&row, "contract_type"))),
        )?;
        option_extend.set_item("contract_size", size_raw.clone())?;
        option_extend.set_item(
            "direction",
            option_extend_src.as_ref().and_then(|src| as_text(mapping_or_attr(src, "direction")))
                .or_else(|| as_text(mapping_or_attr(&row, "direction"))),
        )?;
        option_extend.set_item("historical_volatility", hist_raw.clone())?;
        option_extend.set_item(
            "underlying_symbol",
            option_extend_src.as_ref().and_then(|src| as_text(mapping_or_attr(src, "underlying_symbol")))
                .or_else(|| as_text(mapping_or_attr(&row, "underlying_symbol"))),
        )?;
    }

    let out = PyDict::new(py);
    out.set_item("symbol", as_text(mapping_or_attr(&row, "symbol")).unwrap_or_default())?;
    out.set_item("last_done", as_float(mapping_or_attr(&row, "last_done")))?;
    out.set_item("prev_close", as_float(mapping_or_attr(&row, "prev_close")))?;
    out.set_item("open", as_float(mapping_or_attr(&row, "open")))?;
    out.set_item("high", as_float(mapping_or_attr(&row, "high")))?;
    out.set_item("low", as_float(mapping_or_attr(&row, "low")))?;
    out.set_item("timestamp", as_int(mapping_or_attr(&row, "timestamp")))?;
    out.set_item("volume", as_int(mapping_or_attr(&row, "volume")))?;
    out.set_item("turnover", as_float(mapping_or_attr(&row, "turnover")))?;
    out.set_item("trade_status", to_trade_status(mapping_or_attr(&row, "trade_status")))?;
    out.set_item("option_extend", if extend_has_values { option_extend.into_any() } else { py.None().bind(py).clone().into_any() })?;
    out.set_item("open_interest", open_interest)?;
    out.set_item("implied_volatility", as_float(mapping_or_attr(&row, "implied_volatility")))?;
    out.set_item("implied_volatility_raw", implied_raw.clone())?;
    out.set_item("implied_volatility_decimal", to_decimal_ratio(implied_raw.clone()))?;
    out.set_item("expiry_date", to_iso_date(expiry_raw.clone()))?;
    out.set_item("expiry_date_raw", expiry_raw.clone())?;
    out.set_item("expiry_date_iso", to_iso_date(expiry_raw.clone()))?;
    out.set_item("strike_price", float_from_text(strike_raw.clone()).or_else(|| as_float(mapping_or_attr(&row, "strike_price"))))?;
    out.set_item("strike_price_raw", strike_raw.clone())?;
    out.set_item("contract_multiplier", float_from_text(multiplier_raw.clone()).or_else(|| as_float(mapping_or_attr(&row, "contract_multiplier"))))?;
    out.set_item(
        "contract_type",
        option_extend_src.as_ref().and_then(|src| as_text(mapping_or_attr(src, "contract_type")))
            .or_else(|| as_text(mapping_or_attr(&row, "contract_type"))),
    )?;
    out.set_item("contract_size", float_from_text(size_raw.clone()).or_else(|| as_float(mapping_or_attr(&row, "contract_size"))))?;
    out.set_item(
        "direction",
        option_extend_src.as_ref().and_then(|src| as_text(mapping_or_attr(src, "direction")))
            .or_else(|| as_text(mapping_or_attr(&row, "direction"))),
    )?;
    out.set_item("historical_volatility", float_from_text(hist_raw.clone()).or_else(|| as_float(mapping_or_attr(&row, "historical_volatility"))))?;
    out.set_item("historical_volatility_raw", hist_raw.clone())?;
    out.set_item("historical_volatility_decimal", to_decimal_ratio(hist_raw.clone()))?;
    out.set_item(
        "underlying_symbol",
        option_extend_src.as_ref().and_then(|src| as_text(mapping_or_attr(src, "underlying_symbol")))
            .or_else(|| as_text(mapping_or_attr(&row, "underlying_symbol"))),
    )?;
    Ok(out.unbind())
}

#[pyfunction]
fn quote_api_build_option_chain_strike_contract(py: Python<'_>, row: Bound<'_, PyAny>) -> PyResult<Py<PyDict>> {
    let price_raw = as_text(mapping_or_attr(&row, "price_raw")).or_else(|| as_text(mapping_or_attr(&row, "price")));
    let price = as_float(mapping_or_attr(&row, "price"));
    let out = PyDict::new(py);
    out.set_item("price", price)?;
    out.set_item("price_raw", price_raw.clone())?;
    out.set_item("strike_price", price)?;
    out.set_item("call_symbol", as_text(mapping_or_attr(&row, "call_symbol")))?;
    out.set_item("put_symbol", as_text(mapping_or_attr(&row, "put_symbol")))?;
    if let Some(value) = mapping_or_attr(&row, "standard") {
        out.set_item("standard", value)?;
    } else {
        out.set_item("standard", py.None())?;
    }
    Ok(out.unbind())
}

#[pyfunction]
fn quote_api_build_calc_index_contract(py: Python<'_>, row: Bound<'_, PyAny>) -> PyResult<Py<PyDict>> {
    let implied_raw = as_text(mapping_or_attr(&row, "implied_volatility_raw"))
        .or_else(|| as_text(mapping_or_attr(&row, "implied_volatility")));
    let expiry_raw = as_text(mapping_or_attr(&row, "expiry_date_raw"))
        .or_else(|| as_text(mapping_or_attr(&row, "expiry_date")));
    let strike_raw = as_text(mapping_or_attr(&row, "strike_price_raw"))
        .or_else(|| as_text(mapping_or_attr(&row, "strike_price")));
    let out = PyDict::new(py);
    out.set_item("symbol", as_text(mapping_or_attr(&row, "symbol")).unwrap_or_default())?;
    out.set_item("last_done", as_float(mapping_or_attr(&row, "last_done")))?;
    out.set_item("change_val", as_float(mapping_or_attr(&row, "change_val")))?;
    out.set_item("change_rate", as_float(mapping_or_attr(&row, "change_rate")))?;
    out.set_item("volume", as_int(mapping_or_attr(&row, "volume")))?;
    out.set_item("turnover", as_float(mapping_or_attr(&row, "turnover")))?;
    out.set_item("expiry_date", to_iso_date(expiry_raw.clone()))?;
    out.set_item("expiry_date_raw", expiry_raw.clone())?;
    out.set_item("expiry_date_iso", to_iso_date(expiry_raw.clone()))?;
    out.set_item("strike_price", float_from_text(strike_raw.clone()).or_else(|| as_float(mapping_or_attr(&row, "strike_price"))))?;
    out.set_item("strike_price_raw", strike_raw.clone())?;
    out.set_item("premium", as_float(mapping_or_attr(&row, "premium")))?;
    out.set_item("implied_volatility", as_float(mapping_or_attr(&row, "implied_volatility")))?;
    out.set_item("implied_volatility_raw", implied_raw.clone())?;
    out.set_item("implied_volatility_decimal", to_decimal_ratio(implied_raw.clone()))?;
    out.set_item("open_interest", as_int(mapping_or_attr(&row, "open_interest")))?;
    out.set_item("delta", as_float(mapping_or_attr(&row, "delta")))?;
    out.set_item("gamma", as_float(mapping_or_attr(&row, "gamma")))?;
    out.set_item("theta", as_float(mapping_or_attr(&row, "theta")))?;
    out.set_item("vega", as_float(mapping_or_attr(&row, "vega")))?;
    out.set_item("rho", as_float(mapping_or_attr(&row, "rho")))?;
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(quote_api_build_option_quote_contract, module)?)?;
    module.add_function(wrap_pyfunction!(quote_api_build_option_chain_strike_contract, module)?)?;
    module.add_function(wrap_pyfunction!(quote_api_build_calc_index_contract, module)?)?;
    Ok(())
}

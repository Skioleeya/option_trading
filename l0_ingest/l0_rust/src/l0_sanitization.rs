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

fn nested_value<'py>(obj: &Bound<'py, PyAny>, parent: &str, key: &str) -> Option<Bound<'py, PyAny>> {
    let parent_value = mapping_or_attr(obj, parent)?;
    mapping_or_attr(&parent_value, key)
}

fn safe_float(value: Option<Bound<'_, PyAny>>) -> Option<f64> {
    value.and_then(|inner| extract_float(&inner))
}

fn safe_positive_float(value: Option<Bound<'_, PyAny>>) -> Option<f64> {
    safe_float(value).filter(|parsed| *parsed > 0.0)
}

fn safe_int(value: Option<Bound<'_, PyAny>>) -> Option<i64> {
    value.and_then(|inner| extract_int(&inner))
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

fn infer_opt_type(symbol: &str) -> &'static str {
    let upper = symbol.to_uppercase();
    let base = upper.split('.').next().unwrap_or(upper.as_str());
    let suffix = if base.len() > 8 { &base[base.len() - 8..] } else { base };
    if suffix.contains('P') { "PUT" } else { "CALL" }
}

#[pyfunction]
#[pyo3(signature = (symbol, event_type, strike, arrival_mono, payload, seq_no, now_mono))]
fn l0_sanitize_parse_quote(
    py: Python<'_>,
    symbol: String,
    event_type: i64,
    strike: f64,
    arrival_mono: f64,
    payload: Bound<'_, PyAny>,
    seq_no: i64,
    now_mono: f64,
) -> PyResult<Option<Py<PyDict>>> {
    let bid = safe_positive_float(mapping_or_attr(&payload, "bid"));
    let ask = safe_positive_float(mapping_or_attr(&payload, "ask"));
    let last_price = safe_positive_float(mapping_or_attr(&payload, "last_done"));
    let volume = safe_int(mapping_or_attr(&payload, "volume"));
    let current_volume = safe_float(mapping_or_attr(&payload, "current_volume"));
    let turnover = safe_float(mapping_or_attr(&payload, "turnover"));
    let delta = safe_float(mapping_or_attr(&payload, "delta"));
    let gamma = safe_float(mapping_or_attr(&payload, "gamma"));
    let theta = safe_float(mapping_or_attr(&payload, "theta"));
    let vega = safe_float(mapping_or_attr(&payload, "vega"));

    let mut open_interest = safe_int(mapping_or_attr(&payload, "open_interest"));
    if open_interest.is_none() {
        open_interest = safe_int(nested_value(&payload, "option_extend", "open_interest"));
    }

    let iv_normalized = safe_float(mapping_or_attr(&payload, "implied_volatility_decimal"));
    let iv_raw = nested_value(&payload, "option_extend", "implied_volatility")
        .or_else(|| mapping_or_attr(&payload, "implied_volatility"));
    let mut implied_volatility = None;
    let mut iv_timestamp = None;
    if let Some(iv) = iv_normalized.filter(|value| *value > 0.0) {
        implied_volatility = Some(iv);
        iv_timestamp = Some(now_mono);
    } else if let Some(raw) = safe_float(iv_raw).filter(|value| *value > 0.0) {
        implied_volatility = Some(if raw > 1.0 { raw / 100.0 } else { raw });
        iv_timestamp = Some(now_mono);
    }

    let (bid, ask) = match (bid, ask) {
        (Some(left), Some(right)) if left > right => (None, None),
        other => other,
    };
    let quote_age = if arrival_mono > 0.0 { now_mono - arrival_mono } else { 0.0 };
    let (bid, ask, last_price) = if quote_age > 30.0 {
        (None, None, None)
    } else {
        (bid, ask, last_price)
    };

    let useful = bid.is_some()
        || ask.is_some()
        || last_price.is_some()
        || volume.is_some()
        || open_interest.is_some()
        || implied_volatility.is_some();
    if !useful {
        return Ok(None);
    }

    let out = PyDict::new(py);
    out.set_item("seq_no", seq_no)?;
    out.set_item("event_type", event_type)?;
    out.set_item("symbol", symbol.clone())?;
    out.set_item("strike", strike)?;
    out.set_item("opt_type", infer_opt_type(&symbol))?;
    out.set_item("bid", bid)?;
    out.set_item("ask", ask)?;
    out.set_item("last_price", last_price)?;
    out.set_item("volume", volume)?;
    out.set_item("open_interest", open_interest)?;
    out.set_item("implied_volatility", implied_volatility)?;
    out.set_item("iv_timestamp", iv_timestamp)?;
    out.set_item("delta", delta)?;
    out.set_item("gamma", gamma)?;
    out.set_item("theta", theta)?;
    out.set_item("vega", vega)?;
    out.set_item("current_volume", current_volume)?;
    out.set_item("turnover", turnover)?;
    out.set_item("arrival_mono", arrival_mono)?;
    out.set_item("impact_index", 0.0_f64)?;
    out.set_item("is_sweep", false)?;
    Ok(Some(out.unbind()))
}

#[pyfunction]
#[pyo3(signature = (symbol, arrival_mono, payload, seq_no))]
fn l0_sanitize_parse_depth(
    py: Python<'_>,
    symbol: String,
    arrival_mono: f64,
    payload: Bound<'_, PyAny>,
    seq_no: i64,
) -> PyResult<Option<Py<PyDict>>> {
    let bids = mapping_or_attr(&payload, "bids");
    let asks = mapping_or_attr(&payload, "asks");

    let bid0 = bids
        .as_ref()
        .and_then(|value| value.get_item(0).ok());
    let ask0 = asks
        .as_ref()
        .and_then(|value| value.get_item(0).ok());

    let bid_price = bid0
        .as_ref()
        .and_then(|value| mapping_or_attr(value, "price").or_else(|| value.get_item(0).ok()))
        .and_then(|value| safe_float(Some(value)));
    let bid_size = bid0
        .as_ref()
        .and_then(|value| mapping_or_attr(value, "volume").or_else(|| value.get_item(1).ok()))
        .and_then(|value| safe_int(Some(value)));
    let ask_price = ask0
        .as_ref()
        .and_then(|value| mapping_or_attr(value, "price").or_else(|| value.get_item(0).ok()))
        .and_then(|value| safe_float(Some(value)));
    let ask_size = ask0
        .as_ref()
        .and_then(|value| mapping_or_attr(value, "volume").or_else(|| value.get_item(1).ok()))
        .and_then(|value| safe_int(Some(value)));

    if bid_price.is_none() && ask_price.is_none() {
        return Ok(None);
    }

    let out = PyDict::new(py);
    out.set_item("seq_no", seq_no)?;
    out.set_item("symbol", symbol)?;
    out.set_item("bid", bid_price)?;
    out.set_item("ask", ask_price)?;
    out.set_item("bid_size", bid_size)?;
    out.set_item("ask_size", ask_size)?;
    out.set_item("arrival_mono", arrival_mono)?;
    Ok(Some(out.unbind()))
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(l0_sanitize_parse_quote, module)?)?;
    module.add_function(wrap_pyfunction!(l0_sanitize_parse_depth, module)?)?;
    Ok(())
}

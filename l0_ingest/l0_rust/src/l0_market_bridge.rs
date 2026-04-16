use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};

const ARRIVAL_MONO_NS_PER_SECOND: f64 = 1_000_000_000.0;
const MIN_BOOK_VOLUME: f64 = 1.0;
const DEPTH_IMPACT_SIDE_RATIO: f64 = 0.3;

fn mapping_f64(row: &Bound<'_, PyAny>, key: &str) -> Option<f64> {
    row.call_method1("get", (key,))
        .ok()
        .and_then(|value| value.extract::<Option<f64>>().ok())
        .flatten()
        .filter(|value| value.is_finite())
}

fn mapping_i64(row: &Bound<'_, PyAny>, key: &str) -> Option<i64> {
    row.call_method1("get", (key,))
        .ok()
        .and_then(|value| value.extract::<Option<i64>>().ok())
        .flatten()
}

fn mapping_string(row: &Bound<'_, PyAny>, key: &str) -> Option<String> {
    if let Ok(value) = row.call_method1("get", (key,))
        && let Ok(parsed) = value.extract::<Option<String>>()
        && let Some(cleaned) = parsed.map(|inner| inner.trim().to_string())
        && !cleaned.is_empty()
    {
        return Some(cleaned);
    }
    row.getattr(key)
        .ok()
        .and_then(|value| value.extract::<Option<String>>().ok())
        .flatten()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn attr_f64(row: &Bound<'_, PyAny>, key: &str) -> Option<f64> {
    row.getattr(key)
        .ok()
        .and_then(|value| value.extract::<Option<f64>>().ok())
        .flatten()
        .filter(|value| value.is_finite())
}

fn midpoint(bid: Option<f64>, ask: Option<f64>) -> Option<f64> {
    match (bid, ask) {
        (Some(bid_px), Some(ask_px)) if bid_px > 0.0 && ask_px > 0.0 && ask_px >= bid_px => {
            Some((bid_px + ask_px) * 0.5)
        }
        _ => None,
    }
}

fn positive_or_none(value: Option<f64>) -> Option<f64> {
    value.filter(|inner| *inner > 0.0)
}

fn safe_int_or_none(value: Option<i64>) -> Option<i64> {
    value.filter(|inner| *inner >= 0)
}

fn infer_opt_type(symbol: &str) -> &'static str {
    let base = symbol.split('.').next().unwrap_or(symbol);
    let suffix = if base.len() > 8 { &base[base.len() - 8..] } else { base };
    if suffix.contains('P') { "PUT" } else { "CALL" }
}

fn impact_sign(value: Option<f64>) -> i64 {
    match value.unwrap_or(0.0) {
        inner if inner > 0.0 => 1,
        inner if inner < 0.0 => -1,
        _ => 0,
    }
}

#[pyfunction]
fn l0_market_parse_event(
    py: Python<'_>,
    event: Bound<'_, PyAny>,
    symbol_to_strike: Bound<'_, PyAny>,
) -> PyResult<Option<Py<PyDict>>> {
    let symbol = event
        .call_method1("get", ("symbol",))?
        .extract::<String>()?
        .trim()
        .to_string();
    if symbol.is_empty() || symbol == "\0" {
        return Ok(None);
    }
    let strike = symbol_to_strike
        .call_method1("get", (symbol.clone(),))?
        .extract::<Option<f64>>()?;
    let Some(strike_value) = strike else {
        return Ok(None);
    };
    let event_type = event
        .call_method1("get", ("event_type",))?
        .extract::<Option<i64>>()?
        .filter(|value| (1..=4).contains(value));
    let Some(event_type_value) = event_type else {
        return Ok(None);
    };

    let out = PyDict::new(py);
    out.set_item("seq_no", mapping_i64(&event, "seq_no").unwrap_or(0))?;
    out.set_item("event_type", event_type_value)?;
    out.set_item("trade_type", mapping_string(&event, "trade_type"))?;
    out.set_item("trade_session", mapping_string(&event, "trade_session"))?;
    out.set_item("symbol", symbol.clone())?;
    out.set_item("strike", strike_value)?;
    out.set_item("opt_type", infer_opt_type(&symbol))?;
    out.set_item("bid", positive_or_none(mapping_f64(&event, "bid")))?;
    out.set_item("ask", positive_or_none(mapping_f64(&event, "ask")))?;
    out.set_item("last_price", positive_or_none(mapping_f64(&event, "last_price")))?;
    out.set_item("volume", safe_int_or_none(mapping_i64(&event, "volume")))?;
    out.set_item(
        "bid_volume",
        safe_int_or_none(mapping_i64(&event, "bid_volume")),
    )?;
    out.set_item(
        "ask_volume",
        safe_int_or_none(mapping_i64(&event, "ask_volume")),
    )?;
    out.set_item("open_interest", py.None())?;
    out.set_item("implied_volatility", py.None())?;
    out.set_item("current_volume", mapping_f64(&event, "current_volume"))?;
    out.set_item("turnover", mapping_f64(&event, "turnover"))?;
    out.set_item(
        "arrival_mono",
        mapping_f64(&event, "arrival_mono_ns").unwrap_or(0.0) / ARRIVAL_MONO_NS_PER_SECOND,
    )?;
    out.set_item("impact_index", mapping_f64(&event, "impact_index").unwrap_or(0.0))?;
    out.set_item(
        "is_sweep",
        event.call_method1("get", ("is_sweep", false))?.extract::<bool>()?,
    )?;
    Ok(Some(out.unbind()))
}

#[pyfunction]
fn l0_market_depth_levels(py: Python<'_>, event: Bound<'_, PyAny>) -> PyResult<Py<PyDict>> {
    let volume = attr_f64(&event, "volume").unwrap_or(0.0).max(MIN_BOOK_VOLUME);
    let impact = attr_f64(&event, "impact_index").unwrap_or(0.0);
    let (bid_volume, ask_volume) = if impact > 0.0 {
        (volume, (volume * DEPTH_IMPACT_SIDE_RATIO).max(MIN_BOOK_VOLUME))
    } else if impact < 0.0 {
        ((volume * DEPTH_IMPACT_SIDE_RATIO).max(MIN_BOOK_VOLUME), volume)
    } else {
        (volume, volume)
    };

    let out = PyDict::new(py);
    let bids = PyList::empty(py);
    let asks = PyList::empty(py);
    if let Some(bid) = positive_or_none(attr_f64(&event, "bid")) {
        let row = PyDict::new(py);
        row.set_item("price", bid)?;
        row.set_item("volume", bid_volume)?;
        bids.append(row)?;
    }
    if let Some(ask) = positive_or_none(attr_f64(&event, "ask")) {
        let row = PyDict::new(py);
        row.set_item("price", ask)?;
        row.set_item("volume", ask_volume)?;
        asks.append(row)?;
    }
    out.set_item("bids", bids)?;
    out.set_item("asks", asks)?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (event, previous_price=None, previous_direction=None, bid1=None, ask1=None))]
fn l0_market_trade_payload(
    py: Python<'_>,
    event: Bound<'_, PyAny>,
    previous_price: Option<f64>,
    previous_direction: Option<i64>,
    bid1: Option<f64>,
    ask1: Option<f64>,
) -> PyResult<Option<Py<PyDict>>> {
    let volume = attr_f64(&event, "volume").unwrap_or(0.0);
    if volume <= 0.0 {
        return Ok(None);
    }
    let last_price = positive_or_none(attr_f64(&event, "last_price"));
    let bid = bid1.or_else(|| positive_or_none(attr_f64(&event, "bid")));
    let ask = ask1.or_else(|| positive_or_none(attr_f64(&event, "ask")));
    let mut direction = impact_sign(attr_f64(&event, "impact_index"));
    if let Some(last) = last_price {
        let tick_rule_dir = match previous_price {
            Some(prev) if last > prev => 1,
            Some(prev) if last < prev => -1,
            _ => previous_direction.unwrap_or(0),
        };
        let mid = midpoint(bid, ask);
        if let Some(mid_px) = mid {
            if (last - mid_px).abs() <= 1e-6 {
                direction = tick_rule_dir;
            } else if let Some(ask_px) = ask {
                if last >= (ask_px - 1e-6) {
                    direction = 1;
                } else if let Some(bid_px) = bid {
                    if last <= (bid_px + 1e-6) {
                        direction = -1;
                    } else {
                        direction = tick_rule_dir;
                    }
                }
            } else {
                direction = tick_rule_dir;
            }
        } else {
            direction = tick_rule_dir;
        }
    }
    let trade_type = mapping_string(&event, "trade_type").unwrap_or_else(|| "UNKNOWN".to_string());
    let trade_session = mapping_string(&event, "trade_session").unwrap_or_else(|| "UNKNOWN".to_string());
    let timestamp = py
        .import("time")?
        .call_method0("time")?
        .extract::<f64>()?
        .mul_add(1000.0, 0.0)
        .floor() as i64;
    let out = PyDict::new(py);
    out.set_item("price", last_price.unwrap_or(0.0))?;
    out.set_item("vol", volume)?;
    out.set_item("volume", volume)?;
    out.set_item("timestamp", timestamp)?;
    out.set_item("dir", direction)?;
    out.set_item("direction", direction)?;
    out.set_item("trade_type", trade_type)?;
    out.set_item("trade_session", trade_session)?;
    Ok(Some(out.unbind()))
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(l0_market_parse_event, module)?)?;
    module.add_function(wrap_pyfunction!(l0_market_depth_levels, module)?)?;
    module.add_function(wrap_pyfunction!(l0_market_trade_payload, module)?)?;
    Ok(())
}

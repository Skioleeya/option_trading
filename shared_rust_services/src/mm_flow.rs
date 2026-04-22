use crate::mm_flow_snapshot::{condition_filtered_text, mm_snapshot_metrics_impl};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyModule};

const EPSILON: f64 = 1e-6;
const CONTRACT_MULTIPLIER: f64 = 100.0;
const COMPLEX_DELTA_THRESHOLD: f64 = 50_000.0;

fn valid_price(value: Option<f64>) -> Option<f64> {
    value.filter(|inner| inner.is_finite() && *inner > 0.0)
}

fn near_equal(left: f64, right: f64, epsilon: f64) -> bool {
    (left - right).abs() <= epsilon.max(EPSILON)
}

#[pyfunction]
#[pyo3(signature = (price, bid1=None, ask1=None, prev_price=None, prev_direction=0, epsilon=EPSILON))]
fn mm_tick_rule_direction(
    price: f64,
    bid1: Option<f64>,
    ask1: Option<f64>,
    prev_price: Option<f64>,
    prev_direction: i64,
    epsilon: f64,
) -> PyResult<i64> {
    if !price.is_finite() || price <= 0.0 {
        return Ok(0);
    }
    let bid = valid_price(bid1);
    let ask = valid_price(ask1);
    if let Some(ask_px) = ask
        && price >= (ask_px - epsilon.max(EPSILON))
    {
        return Ok(1);
    }
    if let Some(bid_px) = bid
        && price <= (bid_px + epsilon.max(EPSILON))
    {
        return Ok(-1);
    }

    let tick_dir = match prev_price {
        Some(prev) if price > prev => 1,
        Some(prev) if price < prev => -1,
        _ => prev_direction.signum(),
    };
    if let (Some(bid_px), Some(ask_px)) = (bid, ask)
        && ask_px >= bid_px
    {
        let mid = (bid_px + ask_px) * 0.5;
        if near_equal(price, mid, epsilon) {
            return Ok(tick_dir);
        }
    }
    Ok(tick_dir)
}

#[pyfunction]
#[pyo3(signature = (trade_type=None))]
fn mm_condition_filtered(trade_type: Option<String>) -> PyResult<bool> {
    Ok(condition_filtered_text(trade_type.as_deref()))
}

#[pyfunction]
#[pyo3(signature = (size, open_interest, epsilon=EPSILON))]
fn mm_oi_participation(size: f64, open_interest: f64, epsilon: f64) -> PyResult<f64> {
    if !size.is_finite() || !open_interest.is_finite() || size <= 0.0 || open_interest <= epsilon.max(EPSILON) {
        return Ok(0.0);
    }
    Ok(size / open_interest.max(epsilon.max(EPSILON)))
}

#[pyfunction]
#[pyo3(signature = (direction, size, delta, gamma, multiplier=CONTRACT_MULTIPLIER))]
fn mm_exposure_delta_gamma(
    direction: i64,
    size: f64,
    delta: f64,
    gamma: f64,
    multiplier: f64,
) -> PyResult<(f64, f64)> {
    if !size.is_finite() || size <= 0.0 {
        return Ok((0.0, 0.0));
    }
    let mult = if multiplier.is_finite() && multiplier > 0.0 {
        multiplier
    } else {
        CONTRACT_MULTIPLIER
    };
    let signed = direction.signum() as f64;
    let safe_delta = if delta.is_finite() { delta } else { 0.0 };
    let safe_gamma = if gamma.is_finite() { gamma } else { 0.0 };
    let net_delta = signed * size * mult * safe_delta;
    let net_gamma = size * mult * safe_gamma;
    Ok((net_delta, net_gamma))
}

#[pyfunction]
#[pyo3(signature = (chain_rows=None, epsilon=EPSILON, complex_delta_threshold=COMPLEX_DELTA_THRESHOLD))]
fn mm_snapshot_metrics(
    py: Python<'_>,
    chain_rows: Option<&Bound<'_, PyAny>>,
    epsilon: f64,
    complex_delta_threshold: f64,
) -> PyResult<Py<pyo3::types::PyDict>> {
    mm_snapshot_metrics_impl(py, chain_rows, epsilon, complex_delta_threshold)
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(mm_tick_rule_direction, module)?)?;
    module.add_function(wrap_pyfunction!(mm_condition_filtered, module)?)?;
    module.add_function(wrap_pyfunction!(mm_oi_participation, module)?)?;
    module.add_function(wrap_pyfunction!(mm_exposure_delta_gamma, module)?)?;
    module.add_function(wrap_pyfunction!(mm_snapshot_metrics, module)?)?;
    Ok(())
}


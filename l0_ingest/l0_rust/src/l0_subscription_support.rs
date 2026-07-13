use crate::l0_subscription_selection::{select_targets_impl, symbol_priority_key};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};
use std::collections::{HashMap, HashSet};

const LONGPORT_MAX_SUBSCRIPTIONS: i64 = 500;

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
    select_targets_impl(
        py,
        rows,
        PyList::empty(py).into_any(),
        spot,
        None,
        0.0,
        30,
        600.0,
        0.90,
        5,
    )
}

#[pyfunction]
#[pyo3(signature = (rows, chain_snapshot, spot, first_source_seen_at_mono=None, now_mono=0.0, initial_steps=30, dynamic_after_sec=600.0, coverage=0.90, core_buffer_steps=5))]
fn l0_subscription_select_targets(
    py: Python<'_>,
    rows: Bound<'_, PyAny>,
    chain_snapshot: Bound<'_, PyAny>,
    spot: f64,
    first_source_seen_at_mono: Option<f64>,
    now_mono: f64,
    initial_steps: usize,
    dynamic_after_sec: f64,
    coverage: f64,
    core_buffer_steps: usize,
) -> PyResult<Py<PyDict>> {
    select_targets_impl(
        py,
        rows,
        chain_snapshot,
        spot,
        first_source_seen_at_mono,
        now_mono,
        initial_steps,
        dynamic_after_sec,
        coverage,
        core_buffer_steps,
    )
}

#[pyfunction]
#[pyo3(signature = (target_symbols, mandatory_symbols, subscription_cap, symbol_to_strike, spot=None, symbol_priority=None))]
fn l0_subscription_enforce_cap(
    py: Python<'_>,
    target_symbols: Vec<String>,
    mandatory_symbols: Vec<String>,
    subscription_cap: usize,
    symbol_to_strike: Bound<'_, PyDict>,
    spot: Option<f64>,
    symbol_priority: Option<Bound<'_, PyDict>>,
) -> PyResult<Py<PyDict>> {
    let mut strike_map = HashMap::new();
    for (key, value) in symbol_to_strike.iter() {
        if let (Ok(symbol), Ok(strike)) = (key.extract::<String>(), value.extract::<f64>()) {
            strike_map.insert(symbol, strike);
        }
    }
    let mut priority_map = HashMap::new();
    if let Some(priority_dict) = symbol_priority {
        for (key, value) in priority_dict.iter() {
            if let (Ok(symbol), Ok(priority)) = (key.extract::<String>(), value.extract::<i64>()) {
                priority_map.insert(symbol, priority);
            }
        }
    }
    let mut mandatory: Vec<String> = mandatory_symbols;
    if mandatory.len() > subscription_cap {
        mandatory.sort_by(|left, right| {
            symbol_priority_key(left, spot, &strike_map, &priority_map)
                .partial_cmp(&symbol_priority_key(
                    right,
                    spot,
                    &strike_map,
                    &priority_map,
                ))
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
            symbol_priority_key(left, spot, &strike_map, &priority_map)
                .partial_cmp(&symbol_priority_key(
                    right,
                    spot,
                    &strike_map,
                    &priority_map,
                ))
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
    module.add_function(wrap_pyfunction!(l0_subscription_select_targets, module)?)?;
    module.add_function(wrap_pyfunction!(l0_subscription_enforce_cap, module)?)?;
    Ok(())
}

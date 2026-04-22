use std::cmp::Ordering;

use numpy::IntoPyArray;
use numpy::PyReadonlyArray1;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};
use crate::aggregation_rust_bridge;

pub(crate) fn sanitize(value: f64) -> f64 {
    if value.is_finite() {
        value
    } else {
        0.0
    }
}

pub(crate) fn pick_walls(
    strikes: &[f64],
    call_gex: &[f64],
    put_gex: &[f64],
    spot_ref: f64,
) -> (Option<f64>, Option<f64>, f64, f64) {
    let mut best_call_global: Option<(f64, f64)> = None;
    let mut best_put_global: Option<(f64, f64)> = None;
    let mut best_call_side: Option<(f64, f64)> = None;
    let mut best_put_side: Option<(f64, f64)> = None;
    let use_side = spot_ref.is_finite() && spot_ref > 0.0;

    for i in 0..strikes.len() {
        let strike = strikes[i];
        if !strike.is_finite() {
            continue;
        }
        let call = sanitize(call_gex[i]).max(0.0);
        let put = sanitize(put_gex[i]).max(0.0);

        if best_call_global.map(|(_, g)| call > g).unwrap_or(true) {
            best_call_global = Some((strike, call));
        }
        if best_put_global.map(|(_, g)| put > g).unwrap_or(true) {
            best_put_global = Some((strike, put));
        }

        if use_side && strike >= spot_ref && best_call_side.map(|(_, g)| call > g).unwrap_or(true) {
            best_call_side = Some((strike, call));
        }
        if use_side && strike <= spot_ref && best_put_side.map(|(_, g)| put > g).unwrap_or(true) {
            best_put_side = Some((strike, put));
        }
    }

    let call_pick = best_call_side.or(best_call_global).unwrap_or((0.0, 0.0));
    let put_pick = best_put_side.or(best_put_global).unwrap_or((0.0, 0.0));

    let call_wall = if call_pick.1 > 0.0 {
        Some(call_pick.0)
    } else {
        None
    };
    let put_wall = if put_pick.1 > 0.0 {
        Some(put_pick.0)
    } else {
        None
    };
    (call_wall, put_wall, call_pick.1, put_pick.1)
}

pub(crate) fn cumulative_flip_level(
    strikes: &[f64],
    call_gex: &[f64],
    put_gex: &[f64],
) -> f64 {
    if strikes.is_empty() || call_gex.len() != strikes.len() || put_gex.len() != strikes.len() {
        return 0.0;
    }

    let eps = 1e-12;
    let mut cumulative = 0.0;
    let mut prev_strike: Option<f64> = None;
    let mut prev_cumulative: Option<f64> = None;

    for i in 0..strikes.len() {
        let strike = strikes[i];
        let net = sanitize(call_gex[i]) - sanitize(put_gex[i]);
        cumulative += net;

        if cumulative.abs() <= eps {
            return strike;
        }

        if let (Some(prev_strike), Some(prev_cumulative)) = (prev_strike, prev_cumulative) {
            let cross_up = prev_cumulative < -eps && cumulative > eps;
            let cross_down = prev_cumulative > eps && cumulative < -eps;
            if cross_up || cross_down {
                let denom = cumulative - prev_cumulative;
                if denom.abs() <= eps {
                    return strike;
                }
                let weight = (-prev_cumulative / denom).clamp(0.0, 1.0);
                return prev_strike + (strike - prev_strike) * weight;
            }
        }

        prev_strike = Some(strike);
        prev_cumulative = Some(cumulative);
    }

    0.0
}

#[pyfunction]
fn aggregate_greeks_full<'py>(
    py: Python<'py>,
    strikes: PyReadonlyArray1<'py, f64>,
    call_gex: PyReadonlyArray1<'py, f64>,
    put_gex: PyReadonlyArray1<'py, f64>,
    vanna: PyReadonlyArray1<'py, f64>,
    charm: PyReadonlyArray1<'py, f64>,
) -> PyResult<Py<PyDict>> {
    let strikes_v = strikes.as_array();
    let call_v = call_gex.as_array();
    let put_v = put_gex.as_array();
    let vanna_v = vanna.as_array();
    let charm_v = charm.as_array();

    let n = strikes_v.len();
    if call_v.len() != n || put_v.len() != n || vanna_v.len() != n || charm_v.len() != n {
        return Err(PyValueError::new_err(
            "aggregate_greeks_full requires equal-length input arrays",
        ));
    }

    let mut total_call = 0.0;
    let mut total_put = 0.0;
    let mut total_vanna = 0.0;
    let mut total_charm = 0.0;
    let mut per_contract: Vec<(f64, f64, f64)> = Vec::with_capacity(n);

    for i in 0..n {
        let strike = strikes_v[i];
        let call = sanitize(call_v[i]);
        let put = sanitize(put_v[i]);
        total_call += call;
        total_put += put;
        total_vanna += sanitize(vanna_v[i]);
        total_charm += sanitize(charm_v[i]);
        if strike.is_finite() {
            per_contract.push((strike, call, put));
        }
    }

    per_contract.sort_by(|a, b| {
        if let Some(order) = a.0.partial_cmp(&b.0) {
            order
        } else {
            Ordering::Equal
        }
    });

    let mut unique_strikes: Vec<f64> = Vec::new();
    let mut per_strike_call: Vec<f64> = Vec::new();
    let mut per_strike_put: Vec<f64> = Vec::new();

    for (strike, call, put) in per_contract {
        if let Some(last) = unique_strikes.last() {
            if *last == strike {
                if let Some(last_call) = per_strike_call.last_mut() {
                    *last_call += call;
                }
                if let Some(last_put) = per_strike_put.last_mut() {
                    *last_put += put;
                }
                continue;
            }
        }
        unique_strikes.push(strike);
        per_strike_call.push(call);
        per_strike_put.push(put);
    }

    let flip_level = cumulative_flip_level(&unique_strikes, &per_strike_call, &per_strike_put);

    let out = PyDict::new(py);
    out.set_item("net_gex", total_call - total_put)?;
    out.set_item("total_call_gex", total_call)?;
    out.set_item("total_put_gex", total_put)?;
    out.set_item("net_vanna", total_vanna)?;
    out.set_item("net_charm", total_charm)?;
    out.set_item("flip_level_cumulative", flip_level)?;
    out.set_item("flip_level", flip_level)?;
    out.set_item("strikes", unique_strikes.into_pyarray(py))?;
    out.set_item("per_strike_call_gex", per_strike_call.into_pyarray(py))?;
    out.set_item("per_strike_put_gex", per_strike_put.into_pyarray(py))?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (strikes, call_gex, put_gex, spot_ref))]
fn select_walls(
    strikes: Vec<f64>,
    call_gex: Vec<f64>,
    put_gex: Vec<f64>,
    spot_ref: f64,
) -> PyResult<(f64, f64, f64, f64)> {
    let n = strikes.len();
    if call_gex.len() != n || put_gex.len() != n {
        return Err(PyValueError::new_err(
            "select_walls requires equal-length input arrays",
        ));
    }
    if n == 0 {
        return Ok((0.0, 0.0, 0.0, 0.0));
    }

    let mut best_call_global: Option<(f64, f64)> = None;
    let mut best_put_global: Option<(f64, f64)> = None;
    let mut best_call_side: Option<(f64, f64)> = None;
    let mut best_put_side: Option<(f64, f64)> = None;
    let use_side = spot_ref.is_finite() && spot_ref > 0.0;

    for i in 0..n {
        let strike = strikes[i];
        if !strike.is_finite() {
            continue;
        }
        let call = sanitize(call_gex[i]);
        let put = sanitize(put_gex[i]);

        if best_call_global.map(|(_, g)| call > g).unwrap_or(true) {
            best_call_global = Some((strike, call));
        }
        if best_put_global.map(|(_, g)| put > g).unwrap_or(true) {
            best_put_global = Some((strike, put));
        }

        if use_side && strike >= spot_ref && best_call_side.map(|(_, g)| call > g).unwrap_or(true) {
            best_call_side = Some((strike, call));
        }
        if use_side && strike <= spot_ref && best_put_side.map(|(_, g)| put > g).unwrap_or(true) {
            best_put_side = Some((strike, put));
        }
    }

    let call_pick = best_call_side.or(best_call_global).unwrap_or((0.0, 0.0));
    let put_pick = best_put_side.or(best_put_global).unwrap_or((0.0, 0.0));
    Ok((
        call_pick.0,
        put_pick.0,
        call_pick.1.max(0.0),
        put_pick.1.max(0.0),
    ))
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(aggregate_greeks_full, module)?)?;
    module.add_function(wrap_pyfunction!(select_walls, module)?)?;
    aggregation_rust_bridge::register(module)?;
    Ok(())
}

use std::cmp::Ordering;

use numpy::PyReadonlyArray1;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};

const GEX_SCALE_MILLION: f64 = 1_000_000.0;
const SQRT_2PI: f64 = 2.506_628_274_631_000_2;

fn sanitize(value: f64) -> f64 {
    if value.is_finite() { value } else { 0.0 }
}

fn median(values: &mut [f64]) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));
    let n = values.len();
    if n % 2 == 1 {
        values[n / 2]
    } else {
        (values[n / 2 - 1] + values[n / 2]) * 0.5
    }
}

fn pick_walls(
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
    let call_wall = if call_pick.1 > 0.0 { Some(call_pick.0) } else { None };
    let put_wall = if put_pick.1 > 0.0 { Some(put_pick.0) } else { None };
    (call_wall, put_wall, call_pick.1, put_pick.1)
}

fn interpolate_zero_crossing(grid: &[f64], curve: &[f64], spot_ref: f64) -> f64 {
    if grid.is_empty() || curve.is_empty() || grid.len() != curve.len() {
        return 0.0;
    }
    let eps = 1e-12;
    let mut candidates: Vec<f64> = Vec::new();
    for i in 0..(grid.len() - 1) {
        let y0 = curve[i];
        let y1 = curve[i + 1];
        let x0 = grid[i];
        let x1 = grid[i + 1];
        if y0.abs() <= eps {
            candidates.push(x0);
            continue;
        }
        if y1.abs() <= eps {
            candidates.push(x1);
            continue;
        }
        if y0 * y1 < 0.0 {
            let denom = y1 - y0;
            if denom.abs() <= eps {
                candidates.push(x1);
            } else {
                let weight = (-y0 / denom).clamp(0.0, 1.0);
                candidates.push(x0 + (x1 - x0) * weight);
            }
        }
    }

    if candidates.is_empty() {
        return 0.0;
    }
    if spot_ref.is_finite() && spot_ref > 0.0 {
        let mut best = candidates[0];
        let mut best_dist = (best - spot_ref).abs();
        for &candidate in candidates.iter().skip(1) {
            let dist = (candidate - spot_ref).abs();
            if dist < best_dist {
                best = candidate;
                best_dist = dist;
            }
        }
        best
    } else {
        candidates[0]
    }
}

#[pyfunction]
#[pyo3(signature = (gamma, vanna, charm, spots, strikes, is_call, ivs, t_years, ois, mults))]
fn aggregate_from_greeks<'py>(
    py: Python<'py>,
    gamma: PyReadonlyArray1<'py, f64>,
    vanna: PyReadonlyArray1<'py, f64>,
    charm: PyReadonlyArray1<'py, f64>,
    spots: PyReadonlyArray1<'py, f64>,
    strikes: PyReadonlyArray1<'py, f64>,
    is_call: PyReadonlyArray1<'py, bool>,
    ivs: PyReadonlyArray1<'py, f64>,
    t_years: f64,
    ois: PyReadonlyArray1<'py, f64>,
    mults: PyReadonlyArray1<'py, f64>,
) -> PyResult<Py<PyDict>> {
    let gamma_v = gamma.as_array();
    let vanna_v = vanna.as_array();
    let charm_v = charm.as_array();
    let spots_v = spots.as_array();
    let strikes_v = strikes.as_array();
    let is_call_v = is_call.as_array();
    let ivs_v = ivs.as_array();
    let ois_v = ois.as_array();
    let mults_v = mults.as_array();

    let n = gamma_v.len();
    if vanna_v.len() != n
        || charm_v.len() != n
        || spots_v.len() != n
        || strikes_v.len() != n
        || is_call_v.len() != n
        || ivs_v.len() != n
        || ois_v.len() != n
        || mults_v.len() != n
    {
        return Err(PyValueError::new_err(
            "aggregate_from_greeks requires equal-length input arrays",
        ));
    }

    let mut call_gex: Vec<f64> = vec![0.0; n];
    let mut put_gex: Vec<f64> = vec![0.0; n];
    let mut total_call = 0.0;
    let mut total_put = 0.0;
    let mut net_vanna_exp = 0.0;
    let mut net_charm_exp = 0.0;
    let mut valid_spots: Vec<f64> = Vec::new();
    let t_valid = t_years.is_finite() && t_years > 0.0;

    for i in 0..n {
        let s = spots_v[i];
        let k = strikes_v[i];
        let iv = ivs_v[i];
        let oi = ois_v[i];
        let mult = mults_v[i];
        let valid = t_valid
            && s.is_finite()
            && k.is_finite()
            && iv.is_finite()
            && oi.is_finite()
            && mult.is_finite()
            && s > 0.0
            && k > 0.0
            && iv > 0.0
            && oi >= 0.0
            && mult > 0.0;
        if !valid {
            continue;
        }

        valid_spots.push(s);
        let gex = sanitize(gamma_v[i]) * oi * s * s * mult * 0.01;
        let vanna_exp = sanitize(vanna_v[i]) * oi * mult;
        let charm_exp = sanitize(charm_v[i]) * oi * mult;
        net_vanna_exp += vanna_exp;
        net_charm_exp += charm_exp;

        if is_call_v[i] {
            call_gex[i] = gex;
            total_call += gex;
        } else {
            put_gex[i] = gex;
            total_put += gex;
        }
    }

    let spot_ref = if !valid_spots.is_empty() {
        median(&mut valid_spots)
    } else if !spots_v.is_empty() && spots_v[0].is_finite() {
        spots_v[0]
    } else {
        0.0
    };

    let strikes_vec: Vec<f64> = strikes_v.iter().copied().map(sanitize).collect();
    let (call_wall, put_wall, max_call_gex, max_put_gex) =
        pick_walls(&strikes_vec, &call_gex, &put_gex, spot_ref);

    let out = PyDict::new(py);
    out.set_item("net_gex", (total_call - total_put) / GEX_SCALE_MILLION)?;
    out.set_item("total_call_gex", total_call / GEX_SCALE_MILLION)?;
    out.set_item("total_put_gex", total_put / GEX_SCALE_MILLION)?;
    out.set_item("max_call_gex", max_call_gex)?;
    out.set_item("max_put_gex", max_put_gex)?;
    out.set_item("call_wall", call_wall)?;
    out.set_item("put_wall", put_wall)?;
    out.set_item("net_vanna", net_vanna_exp / GEX_SCALE_MILLION)?;
    out.set_item("net_charm", net_charm_exp / GEX_SCALE_MILLION)?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (strikes, is_call, ivs, ois, mults, t_years, spot, r, q))]
fn estimate_zero_gamma_level(
    strikes: PyReadonlyArray1<'_, f64>,
    is_call: PyReadonlyArray1<'_, bool>,
    ivs: PyReadonlyArray1<'_, f64>,
    ois: PyReadonlyArray1<'_, f64>,
    mults: PyReadonlyArray1<'_, f64>,
    t_years: f64,
    spot: f64,
    r: f64,
    q: f64,
) -> PyResult<f64> {
    let strikes_v = strikes.as_array();
    let is_call_v = is_call.as_array();
    let ivs_v = ivs.as_array();
    let ois_v = ois.as_array();
    let mults_v = mults.as_array();

    let n = strikes_v.len();
    if is_call_v.len() != n || ivs_v.len() != n || ois_v.len() != n || mults_v.len() != n {
        return Err(PyValueError::new_err(
            "estimate_zero_gamma_level requires equal-length input arrays",
        ));
    }
    if n == 0 || !t_years.is_finite() || t_years <= 0.0 {
        return Ok(0.0);
    }

    let mut valid_strikes: Vec<f64> = Vec::new();
    let mut valid_calls: Vec<bool> = Vec::new();
    let mut valid_ivs: Vec<f64> = Vec::new();
    let mut valid_ois: Vec<f64> = Vec::new();
    let mut valid_mults: Vec<f64> = Vec::new();

    for i in 0..n {
        let strike = strikes_v[i];
        let iv = ivs_v[i];
        let oi = ois_v[i];
        let mult = mults_v[i];
        let valid = strike.is_finite()
            && iv.is_finite()
            && oi.is_finite()
            && mult.is_finite()
            && strike > 0.0
            && iv > 0.0
            && oi >= 0.0
            && mult > 0.0;
        if !valid {
            continue;
        }
        valid_strikes.push(strike);
        valid_calls.push(is_call_v[i]);
        valid_ivs.push(iv);
        valid_ois.push(oi);
        valid_mults.push(mult);
    }

    if valid_strikes.is_empty() {
        return Ok(0.0);
    }

    let mut strikes_for_median = valid_strikes.clone();
    let median_strike = median(&mut strikes_for_median);
    let spot_ref = if spot.is_finite() && spot > 0.0 { spot } else { median_strike };

    let min_strike = valid_strikes.iter().copied().fold(f64::INFINITY, f64::min);
    let max_strike = valid_strikes
        .iter()
        .copied()
        .fold(f64::NEG_INFINITY, f64::max);
    let low = f64::max(1e-6, f64::min(min_strike, spot_ref) * 0.90);
    let high = f64::max(low + 1e-6, f64::max(max_strike, spot_ref) * 1.10);
    if !low.is_finite() || !high.is_finite() || high <= low {
        return Ok(0.0);
    }

    let grid_n = 161usize;
    let step = (high - low) / (grid_n as f64 - 1.0);
    let sqrt_t = t_years.sqrt();
    let eq_t = (-q * t_years).exp();

    let mut grid: Vec<f64> = Vec::with_capacity(grid_n);
    let mut net_curve: Vec<f64> = Vec::with_capacity(grid_n);

    for idx in 0..grid_n {
        let s = low + step * idx as f64;
        let safe_s = s.max(1e-12);
        let mut net = 0.0;

        for j in 0..valid_strikes.len() {
            let strike = valid_strikes[j];
            let iv = valid_ivs[j];
            let oi = valid_ois[j];
            let mult = valid_mults[j];
            let denom = (safe_s * iv * sqrt_t).max(1e-12);
            let d1 = ((safe_s / strike).ln() + (r - q + 0.5 * iv * iv) * t_years) / (iv * sqrt_t);
            let nd1 = (-0.5 * d1 * d1).exp() / SQRT_2PI;
            let gamma = eq_t * nd1 / denom;
            let gex = gamma * oi * mult * s * s * 0.01 / GEX_SCALE_MILLION;
            net += if valid_calls[j] { gex } else { -gex };
        }

        grid.push(s);
        net_curve.push(if net.is_finite() { net } else { 0.0 });
    }

    Ok(interpolate_zero_crossing(&grid, &net_curve, spot_ref))
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(aggregate_from_greeks, module)?)?;
    module.add_function(wrap_pyfunction!(estimate_zero_gamma_level, module)?)?;
    Ok(())
}

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;

const ALPHA_BOUNDS: (f64, f64) = (0.001, 5.0);
const RHO_BOUNDS: (f64, f64) = (-0.999, 0.999);
const NU_BOUNDS: (f64, f64) = (0.001, 5.0);
const ATM_EPS: f64 = 1e-4;
const LOG_CHI_EPS: f64 = 1e-12;

fn clamp(value: f64, bounds: (f64, f64)) -> f64 {
    value.clamp(bounds.0, bounds.1)
}

fn validate_scalar(name: &str, value: f64) -> PyResult<()> {
    if value.is_finite() {
        Ok(())
    } else {
        Err(PyValueError::new_err(format!("{name} must be finite")))
    }
}

fn validate_positive(name: &str, value: f64) -> PyResult<()> {
    validate_scalar(name, value)?;
    if value > 0.0 {
        Ok(())
    } else {
        Err(PyValueError::new_err(format!("{name} must be > 0")))
    }
}

fn validate_bounds(name: &str, value: f64, bounds: (f64, f64)) -> PyResult<()> {
    validate_scalar(name, value)?;
    if value >= bounds.0 && value <= bounds.1 {
        Ok(())
    } else {
        Err(PyValueError::new_err(format!(
            "{name} must be within [{}, {}]",
            bounds.0, bounds.1
        )))
    }
}

fn log_chi(z: f64, rho: f64) -> f64 {
    if z.abs() < 1e-8 {
        return 1.0;
    }
    let disc = (1.0 - 2.0 * rho * z + z * z).max(0.0).sqrt();
    let arg = (disc + z - rho) / (1.0 - rho);
    if !(arg.is_finite()) || arg <= 0.0 {
        return 1.0;
    }
    let out = arg.ln() / z;
    if out.is_finite() { out } else { 1.0 }
}

fn sabr_iv_core(strike: f64, forward: f64, ttm: f64, alpha: f64, beta: f64, rho: f64, nu: f64) -> f64 {
    if ttm <= 0.0 || alpha <= 0.0 {
        return 0.0;
    }

    let f = forward;
    let mut k = strike;
    if k <= 0.0 {
        k = 1e-9;
    }

    let fk_mid = (f * k).abs().sqrt();
    let log_fk = if (f - k).abs() > 1e-9 { (f / k).ln() } else { 0.0 };
    let fk_beta = fk_mid.powf(1.0 - beta);
    let one_minus_beta = 1.0 - beta;

    if ((f - k).abs() / f.abs().max(1e-9)) < ATM_EPS {
        let z_a = alpha / fk_beta
            * (1.0
                + (one_minus_beta * one_minus_beta / 24.0)
                    * (alpha * alpha / fk_mid.powf(2.0 - 2.0 * beta))
                + (rho * beta * nu * alpha) / (4.0 * fk_mid.powf(1.0 - beta))
                + (2.0 - 3.0 * rho * rho) * nu * nu / 24.0)
            * ttm;
        return alpha / fk_beta * (1.0 + z_a);
    }

    let z = (nu / alpha) * fk_beta * log_fk;
    let denom = log_chi(z, rho);
    let z_chi = if denom.abs() < LOG_CHI_EPS { z } else { z / denom };

    let a = alpha
        / (fk_beta
            * (1.0
                + (one_minus_beta * one_minus_beta / 24.0) * log_fk * log_fk
                + (one_minus_beta.powi(4) / 1920.0) * log_fk.powi(4)));
    let b = 1.0
        + ((one_minus_beta * one_minus_beta / 24.0) * (alpha * alpha / fk_mid.powf(2.0 - 2.0 * beta))
            + (rho * beta * nu * alpha) / (4.0 * fk_mid.powf(1.0 - beta))
            + (2.0 - 3.0 * rho * rho) * nu * nu / 24.0)
            * ttm;
    a * z_chi * b
}

fn residual_mse_for_params(
    strikes: &[f64],
    market_ivs: &[f64],
    forward: f64,
    ttm: f64,
    alpha: f64,
    beta: f64,
    rho: f64,
    nu: f64,
) -> f64 {
    let mut sum_sq = 0.0;
    for idx in 0..strikes.len() {
        let model = sabr_iv_core(strikes[idx], forward, ttm, alpha, beta, rho, nu);
        let diff = model - market_ivs[idx];
        sum_sq += diff * diff;
    }
    sum_sq / strikes.len() as f64
}

fn objective_rmse_for_params(
    strikes: &[f64],
    market_ivs: &[f64],
    forward: f64,
    ttm: f64,
    alpha: f64,
    beta: f64,
    rho: f64,
    nu: f64,
) -> f64 {
    residual_mse_for_params(strikes, market_ivs, forward, ttm, alpha, beta, rho, nu).sqrt()
}

fn gradient_fd(raw: [f64; 3], strikes: &[f64], market_ivs: &[f64], forward: f64, ttm: f64, beta: f64) -> [f64; 3] {
    let mut grad = [0.0; 3];
    let step_base = 1e-4;
    for i in 0..3 {
        let step = step_base * raw[i].abs().max(1.0);
        let mut plus = raw;
        let mut minus = raw;
        plus[i] += step;
        minus[i] -= step;
        plus[i] = clamp(plus[i], match i {
            0 => ALPHA_BOUNDS,
            1 => RHO_BOUNDS,
            _ => NU_BOUNDS,
        });
        minus[i] = clamp(minus[i], match i {
            0 => ALPHA_BOUNDS,
            1 => RHO_BOUNDS,
            _ => NU_BOUNDS,
        });
        let loss_plus = objective_rmse_for_params(strikes, market_ivs, forward, ttm, plus[0], beta, plus[1], plus[2]);
        let loss_minus = objective_rmse_for_params(strikes, market_ivs, forward, ttm, minus[0], beta, minus[1], minus[2]);
        grad[i] = (loss_plus - loss_minus) / (2.0 * step);
    }
    grad
}

#[pyfunction]
#[pyo3(signature = (strike, forward, ttm, alpha, beta, rho, nu))]
fn sabr_iv(
    strike: f64,
    forward: f64,
    ttm: f64,
    alpha: f64,
    beta: f64,
    rho: f64,
    nu: f64,
) -> PyResult<f64> {
    validate_positive("strike", strike)?;
    validate_positive("forward", forward)?;
    validate_positive("ttm", ttm)?;
    validate_bounds("alpha", alpha, ALPHA_BOUNDS)?;
    validate_scalar("beta", beta)?;
    if !(0.0..=1.0).contains(&beta) {
        return Err(PyValueError::new_err("beta must be within [0, 1]"));
    }
    validate_bounds("rho", rho, RHO_BOUNDS)?;
    validate_bounds("nu", nu, NU_BOUNDS)?;
    Ok(sabr_iv_core(strike, forward, ttm, alpha, beta, rho, nu))
}

#[pyfunction]
#[pyo3(signature = (strikes, market_ivs, forward, ttm, beta, alpha_init, rho_init, nu_init, max_iter=1000, tol=1e-8))]
fn calibrate_sabr(
    strikes: Vec<f64>,
    market_ivs: Vec<f64>,
    forward: f64,
    ttm: f64,
    beta: f64,
    alpha_init: f64,
    rho_init: f64,
    nu_init: f64,
    max_iter: usize,
    tol: f64,
) -> PyResult<(f64, f64, f64, f64)> {
    validate_positive("forward", forward)?;
    validate_positive("ttm", ttm)?;
    validate_scalar("beta", beta)?;
    if !(0.0..=1.0).contains(&beta) {
        return Err(PyValueError::new_err("beta must be within [0, 1]"));
    }
    validate_bounds("alpha_init", alpha_init, ALPHA_BOUNDS)?;
    validate_bounds("rho_init", rho_init, RHO_BOUNDS)?;
    validate_bounds("nu_init", nu_init, NU_BOUNDS)?;
    validate_scalar("tol", tol)?;
    if tol <= 0.0 {
        return Err(PyValueError::new_err("tol must be > 0"));
    }
    if strikes.len() != market_ivs.len() {
        return Err(PyValueError::new_err(
            "calibrate_sabr requires equal-length strikes and market_ivs",
        ));
    }
    if strikes.len() < 3 {
        return Err(PyValueError::new_err("calibrate_sabr requires at least 3 observations"));
    }

    for idx in 0..strikes.len() {
        validate_positive("strike", strikes[idx])?;
        validate_positive("market_iv", market_ivs[idx])?;
    }

    let mut raw = [
        clamp(alpha_init, ALPHA_BOUNDS),
        clamp(rho_init, RHO_BOUNDS),
        clamp(nu_init, NU_BOUNDS),
    ];
    let mut m = [0.0; 3];
    let mut v = [0.0; 3];
    let beta1 = 0.9;
    let beta2 = 0.999;
    let adam_eps = 1e-8;
    let lr = [0.12, 0.05, 0.12];
    let mut best_raw = raw;
    let mut best_loss = objective_rmse_for_params(
        &strikes,
        &market_ivs,
        forward,
        ttm,
        best_raw[0],
        beta,
        best_raw[1],
        best_raw[2],
    );

    for step_idx in 1..=max_iter {
        let loss = objective_rmse_for_params(&strikes, &market_ivs, forward, ttm, raw[0], beta, raw[1], raw[2]);
        if loss < best_loss {
            best_loss = loss;
            best_raw = raw;
        }
        if loss <= tol {
            break;
        }

        let grad = gradient_fd(raw, &strikes, &market_ivs, forward, ttm, beta);
        let step_f = step_idx as f64;
        for i in 0..3 {
            m[i] = beta1 * m[i] + (1.0 - beta1) * grad[i];
            v[i] = beta2 * v[i] + (1.0 - beta2) * grad[i] * grad[i];
            let m_hat = m[i] / (1.0 - beta1.powf(step_f));
            let v_hat = v[i] / (1.0 - beta2.powf(step_f));
            raw[i] = clamp(
                raw[i] - lr[i] * m_hat / (v_hat.sqrt() + adam_eps),
                match i {
                    0 => ALPHA_BOUNDS,
                    1 => RHO_BOUNDS,
                    _ => NU_BOUNDS,
                },
            );
        }
    }

    let residual_mse = residual_mse_for_params(
        &strikes,
        &market_ivs,
        forward,
        ttm,
        best_raw[0],
        beta,
        best_raw[1],
        best_raw[2],
    );

    Ok((best_raw[0], best_raw[1], best_raw[2], residual_mse))
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(sabr_iv, module)?)?;
    module.add_function(wrap_pyfunction!(calibrate_sabr, module)?)?;
    Ok(())
}

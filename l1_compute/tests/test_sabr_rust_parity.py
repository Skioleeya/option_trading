from __future__ import annotations

import math
import random

import pytest

import l1_compute.iv.sabr_calibrator as sabr_mod
from l1_compute.iv.sabr_calibrator import SABRCalibrator, SABRParams, _sabr_implied_vol
import shared_rust.services as shared_rust_services


RNG = random.Random(20260402)


def _python_objective(
    params: tuple[float, float, float],
    strikes: list[float],
    market_ivs: list[float],
    forward: float,
    ttm: float,
    beta: float,
) -> float:
    alpha, rho, nu = params
    if not (0.001 <= alpha <= 5.0 and -0.999 <= rho <= 0.999 and 0.001 <= nu <= 5.0):
        return 1e6

    total = 0.0
    for strike, market_iv in zip(strikes, market_ivs):
        diff = _sabr_implied_vol(forward, strike, ttm, alpha, beta, rho, nu) - market_iv
        total += diff * diff
    return math.sqrt(total / max(len(strikes), 1))


def _synthetic_case(seed: int) -> tuple[list[float], list[float], float, float, float, float, float]:
    rng = random.Random(seed)
    forward = rng.uniform(450.0, 650.0)
    ttm = rng.uniform(0.001, 0.05)
    beta = 0.5
    alpha = rng.uniform(0.12, 0.35)
    rho = rng.uniform(-0.1, 0.1)
    nu = rng.uniform(0.05, 0.15)
    strikes = [forward + offset for offset in (-8.0, -6.0, -4.0, -2.0, 0.0)]
    market_ivs = [
        shared_rust_services.sabr_iv(strike, forward, ttm, alpha, beta, rho, nu)
        for strike in strikes
    ]
    return strikes, market_ivs, forward, ttm, alpha, rho, nu


def _assert_bounds(params: SABRParams) -> None:
    assert 0.001 <= params.alpha <= 5.0
    assert -0.999 <= params.rho <= 0.999
    assert 0.001 <= params.nu <= 5.0


def _mean_squared_error(
    strikes: list[float],
    market_ivs: list[float],
    forward: float,
    ttm: float,
    beta: float,
    params: SABRParams,
) -> float:
    total = 0.0
    for strike, market_iv in zip(strikes, market_ivs):
        model_iv = shared_rust_services.sabr_iv(
            strike,
            forward,
            ttm,
            params.alpha,
            beta,
            params.rho,
            params.nu,
        )
        diff = model_iv - market_iv
        total += diff * diff
    return total / max(len(strikes), 1)


@pytest.mark.parametrize("seed", range(50))
def test_sabr_iv_matches_python_reference(seed: int) -> None:
    rng = random.Random(seed)
    forward = rng.uniform(1.0, 800.0)
    strike = rng.uniform(1.0, 800.0)
    ttm = rng.uniform(0.0005, 2.0)
    alpha = rng.uniform(0.001, 2.0)
    beta = rng.uniform(0.0, 1.0)
    rho = rng.uniform(-0.999, 0.999)
    nu = rng.uniform(0.001, 3.0)

    rust = shared_rust_services.sabr_iv(strike, forward, ttm, alpha, beta, rho, nu)
    ref = _sabr_implied_vol(forward, strike, ttm, alpha, beta, rho, nu)
    assert math.isclose(rust, ref, rel_tol=1e-10, abs_tol=1e-12)


@pytest.mark.parametrize("seed", range(20))
def test_calibrate_sabr_parity_or_known_fixture(seed: int) -> None:
    strikes, market_ivs, forward, ttm, alpha_true, rho_true, nu_true = _synthetic_case(seed)
    beta = 0.5

    rust_alpha, rust_rho, rust_nu, rust_mse = shared_rust_services.calibrate_sabr(
        strikes,
        market_ivs,
        forward,
        ttm,
        beta,
        0.20,
        -0.30,
        0.40,
        1000,
        1e-8,
    )

    assert math.isfinite(rust_mse)
    assert 0.001 <= rust_alpha <= 5.0
    assert -0.999 <= rust_rho <= 0.999
    assert 0.001 <= rust_nu <= 5.0
    rust_params = SABRParams(
        alpha=rust_alpha,
        rho=rust_rho,
        nu=rust_nu,
        beta=beta,
        forward=forward,
        ttm=ttm,
        calibration_error=rust_mse,
        calibrated_at=0.0,
    )
    rust_model_mse = _mean_squared_error(strikes, market_ivs, forward, ttm, beta, rust_params)
    assert rust_model_mse < 1e-4
    assert math.isclose(rust_model_mse, rust_mse, rel_tol=1e-9, abs_tol=1e-12)

    calibrator = SABRCalibrator(beta=beta)
    ok = calibrator.calibrate({strike: iv for strike, iv in zip(strikes, market_ivs)}, forward, ttm)
    assert calibrator.params is not None
    _assert_bounds(calibrator.params)
    assert ok == calibrator.params.is_valid

    calibrator_model_mse = _mean_squared_error(strikes, market_ivs, forward, ttm, beta, calibrator.params)
    assert calibrator_model_mse < 1e-4
    assert math.isclose(
        calibrator_model_mse,
        calibrator.params.calibration_error,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )

    strike = forward * 1.01
    direct = shared_rust_services.sabr_iv(
        strike,
        forward,
        ttm,
        calibrator.params.alpha,
        beta,
        calibrator.params.rho,
        calibrator.params.nu,
    )
    wrapped = calibrator.interpolate(strike, ttm)
    assert math.isclose(wrapped, direct, rel_tol=1e-10, abs_tol=1e-12)


def test_calibrate_uses_lightweight_fill_for_small_inputs() -> None:
    calibrator = SABRCalibrator(beta=0.5)
    ok = calibrator.calibrate({560.0: 0.20, 565.0: 0.21}, forward=562.0, ttm=0.01)
    assert ok is False
    assert calibrator.params is not None
    assert calibrator.params.calibration_error == float("inf")


def test_rust_owner_unavailable_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sabr_mod, "_RUST_AVAILABLE", False)
    monkeypatch.setattr(sabr_mod, "_rust_calibrate_sabr", None)
    monkeypatch.setattr(sabr_mod, "_rust_sabr_iv", None)

    calibrator = SABRCalibrator(beta=0.5)
    with pytest.raises(RuntimeError, match="shared_rust.services.calibrate_sabr unavailable"):
        calibrator.calibrate({560.0: 0.20, 565.0: 0.21, 570.0: 0.22}, forward=562.0, ttm=0.01)

    calibrator._params = SABRParams(alpha=0.2, rho=-0.3, nu=0.4, beta=0.5, forward=562.0, ttm=0.01)
    with pytest.raises(RuntimeError, match="shared_rust.services.sabr_iv unavailable"):
        calibrator.interpolate(560.0, 0.01)

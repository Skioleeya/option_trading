from __future__ import annotations

import math

import numpy as np
import pytest

from l1_compute.analysis.bsm_fast import _bsm_batch_numpy
from shared_rust.services import bsm_batch_numpy_tier


def _reference_bsm(
    spots: np.ndarray,
    strikes: np.ndarray,
    ivs: np.ndarray,
    t_years: float,
    is_call: np.ndarray,
    r: float,
    q: float,
) -> dict[str, np.ndarray]:
    sqrt_t = math.sqrt(t_years)
    eq_t = math.exp(-q * t_years)
    er_t = math.exp(-r * t_years)

    safe_iv = np.where(ivs > 0.0, ivs, 1e-8)
    safe_s = np.where(spots > 0.0, spots, 1e-8)
    safe_k = np.where(strikes > 0.0, strikes, 1e-8)
    d1 = (np.log(safe_s / safe_k) + (r - q + 0.5 * safe_iv**2) * t_years) / (safe_iv * sqrt_t)
    d2 = d1 - safe_iv * sqrt_t

    cdf = 0.5 * (1.0 + np.vectorize(math.erf)(d1 / math.sqrt(2.0)))
    cdf_n = 0.5 * (1.0 + np.vectorize(math.erf)(-d1 / math.sqrt(2.0)))
    cdf2 = 0.5 * (1.0 + np.vectorize(math.erf)(d2 / math.sqrt(2.0)))
    cdf2_n = 0.5 * (1.0 + np.vectorize(math.erf)(-d2 / math.sqrt(2.0)))
    nd1 = np.exp(-0.5 * d1**2) / math.sqrt(2.0 * math.pi)

    delta = np.where(is_call, eq_t * cdf, -eq_t * cdf_n)
    gamma = eq_t * nd1 / (safe_s * safe_iv * sqrt_t)
    vega = safe_s * eq_t * nd1 * sqrt_t * 0.01
    vanna = -eq_t * nd1 * d2 / safe_iv * 0.01

    charm_num = 2.0 * (r - q) * t_years - d2 * safe_iv * sqrt_t
    charm_den = 2.0 * t_years * safe_iv * sqrt_t
    charm_call = (q * eq_t * cdf - eq_t * nd1 * charm_num / charm_den) / 365.0
    charm_put = (-q * eq_t * cdf_n - eq_t * nd1 * charm_num / charm_den) / 365.0
    charm = np.where(is_call, charm_call, charm_put)

    theta_call = (
        -(safe_s * safe_iv * eq_t * nd1) / (2.0 * sqrt_t) - r * safe_k * er_t * cdf2 + q * safe_s * eq_t * cdf
    ) / 365.0
    theta_put = (
        -(safe_s * safe_iv * eq_t * nd1) / (2.0 * sqrt_t) + r * safe_k * er_t * cdf2_n - q * safe_s * eq_t * cdf_n
    ) / 365.0
    theta = np.where(is_call, theta_call, theta_put)

    valid = (ivs > 0.0) & (spots > 0.0) & (strikes > 0.0) & (t_years > 0.0)
    for arr in (delta, gamma, vega, vanna, charm, theta):
        arr[~valid] = 0.0
    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "vanna": vanna,
        "charm": charm,
        "theta": theta,
    }


@pytest.mark.parametrize("seed", list(range(50)))
def test_bsm_rust_matches_reference(seed: int) -> None:
    rng = np.random.default_rng(seed)
    n = 64
    spots = rng.uniform(450.0, 650.0, n).astype(np.float64)
    strikes = rng.uniform(400.0, 700.0, n).astype(np.float64)
    ivs = rng.uniform(0.05, 1.00, n).astype(np.float64)
    is_call = rng.integers(0, 2, size=n).astype(bool)
    t_years = float(rng.uniform(0.0003, 0.0200))
    r = float(rng.uniform(0.00, 0.08))
    q = float(rng.uniform(0.00, 0.03))

    rust = bsm_batch_numpy_tier(spots, strikes, ivs, t_years, is_call, r, q)
    ref = _reference_bsm(spots, strikes, ivs, t_years, is_call, r, q)

    for key in ("delta", "gamma", "vega", "vanna", "charm", "theta"):
        assert np.allclose(np.asarray(rust[key]), ref[key], rtol=1e-10, atol=1e-12), key


def test_bsm_atm_call_delta_sanity() -> None:
    out = bsm_batch_numpy_tier(
        np.array([560.0], dtype=np.float64),
        np.array([560.0], dtype=np.float64),
        np.array([0.20], dtype=np.float64),
        0.002,
        np.array([True], dtype=np.bool_),
        0.05,
        0.0,
    )
    delta = float(np.asarray(out["delta"])[0])
    assert 0.4 < delta < 0.6


def test_norm_cdf_track_scipy_when_available() -> None:
    scipy = pytest.importorskip("scipy.special")
    x = np.linspace(-8.0, 8.0, 10000, dtype=np.float64)
    s = np.ones_like(x)
    iv = np.ones_like(x)
    t = 1.0
    k = s / np.exp(x - 0.5)
    calls = np.ones_like(x, dtype=np.bool_)
    out = bsm_batch_numpy_tier(s, k, iv, t, calls, 0.0, 0.0)
    delta = np.asarray(out["delta"], dtype=np.float64)
    assert np.allclose(delta, scipy.ndtr(x), rtol=1e-14, atol=1e-14)


def test_bsm_tier3_requires_rust_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "l1_compute.analysis.bsm_fast.rust_bsm_batch_numpy_tier",
        lambda **_: (_ for _ in ()).throw(RuntimeError("forced-rust-bsm-fail")),
    )
    with pytest.raises(RuntimeError, match="forced-rust-bsm-fail"):
        _bsm_batch_numpy(
            np.array([560.0], dtype=np.float64),
            np.array([560.0], dtype=np.float64),
            np.array([0.20], dtype=np.float64),
            0.002,
            np.array([True], dtype=np.bool_),
            0.05,
            0.0,
        )

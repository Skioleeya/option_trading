"""SABR Calibrator — Full scipy.optimize SABR smile calibration.

SABR Model (Hagan et al. 2002):
    σ_SABR(K, F, T; α, β, ρ, ν)

Parameters:
    α  (alpha): ATM volatility level
    β  (beta) : CEV exponent (fixed at 0.5 for equity index options)
    ρ  (rho)  : spot-vol correlation (skew direction; ρ < 0 for index put skew)
    ν  (nu)   : vol-of-vol (controls smile curvature)

Calibration strategy:
    - Use scipy.optimize.minimize (L-BFGS-B) with market IV observations
    - Regularisation: penalise parameter boundary violations
    - Re-calibrate every `calibration_interval_seconds` seconds (default: 120s)
    - Thread-safe: calibration happens off the asyncio event loop

Usage::

    calibrator = SABRCalibrator(beta=0.5)
    market_ivs  = {560.0: 0.21, 555.0: 0.23, 565.0: 0.20, ...}
    calibrator.calibrate(market_ivs, forward=560.5, ttm=0.002)
    iv = calibrator.interpolate(strike=558.0, ttm=0.002)
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Try scipy
try:
    from scipy.optimize import minimize  # type: ignore
    _SCIPY_AVAILABLE = True
    logger.info("[SABRCalibrator] scipy.optimize available — full SABR calibration enabled.")
except ImportError:
    _SCIPY_AVAILABLE = False
    logger.warning("[SABRCalibrator] scipy not available — using linear skew fallback.")

# Fixed CEV exponent for equity index options
_BETA: float = 0.5
# ATM window: calibrate using strikes within ±10 points
_ATM_WINDOW: float = 10.0
# Calibration interval: 120s between recalibrations
_CALIBRATION_INTERVAL: float = 120.0
# Parameter bounds: (alpha, rho, nu)
_ALPHA_BOUNDS = (0.001, 5.0)
_RHO_BOUNDS   = (-0.999, 0.999)
_NU_BOUNDS    = (0.001, 5.0)


@dataclass
class SABRParams:
    """Calibrated SABR parameters."""
    alpha: float = 0.20    # ATM vol level
    rho:   float = -0.30   # spot-vol correlation (negative for index)
    nu:    float = 0.40    # vol-of-vol
    beta:  float = _BETA
    forward: float = 0.0
    ttm: float = 0.0
    calibration_error: float = float("inf")
    calibrated_at: float = 0.0

    @property
    def is_valid(self) -> bool:
        return self.calibration_error < 0.01  # < 1% RMSE


def _sabr_implied_vol(
    forward: float,
    strike: float,
    ttm: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
) -> float:
    """SABR implied volatility (Hagan et al. 2002, normalised eq. 2.17b).

    Handles the ATM limit (K → F) and near-zero cases safely.
    Returns approximate Black volatility in decimal form.
    """
    if ttm <= 0 or alpha <= 0:
        return 0.0

    F, K = forward, strike
    if K <= 0:
        K = 1e-9

    epsilon = abs((F - K) / max(F, 1e-9))
    FK_mid = math.sqrt(abs(F * K))      # geometric midpoint
    log_fk = math.log(F / K) if abs(F - K) > 1e-9 else 0.0

    # ATM shortcut (Hagan eq. 2.17a)
    if epsilon < 1e-4:
        FK_beta = FK_mid ** (1.0 - beta)
        z_A = (
            alpha / (FK_beta)
            * (1.0
               + ((1.0 - beta) ** 2 / 24.0) * (alpha ** 2 / FK_mid ** (2.0 - 2 * beta))
               + (rho * beta * nu * alpha) / (4.0 * FK_mid ** (1.0 - beta))
               + (2.0 - 3.0 * rho ** 2) * nu ** 2 / 24.0)
            * ttm
        )
        # First-order expansion around ATM
        return alpha / FK_beta * (1.0 + z_A)

    # General case (Hagan eq. 2.17b)
    FK_beta = FK_mid ** (1.0 - beta)

    z = (nu / alpha) * FK_beta * log_fk
    denom = _log_chi(z, rho)
    if abs(denom) < 1e-12:
        denom = 1.0
    z_chi = z / denom

    A = alpha / (FK_beta * (
        1.0
        + ((1.0 - beta) ** 2 / 24.0) * log_fk ** 2
        + ((1.0 - beta) ** 4 / 1920.0) * log_fk ** 4
    ))

    B = 1.0 + (
        ((1.0 - beta) ** 2 / 24.0) * (alpha ** 2 / FK_mid ** (2.0 - 2.0 * beta))
        + (rho * beta * nu * alpha) / (4.0 * FK_mid ** (1.0 - beta))
        + (2.0 - 3.0 * rho ** 2) * nu ** 2 / 24.0
    ) * ttm

    return A * z_chi * B


def _log_chi(z: float, rho: float) -> float:
    """log(χ(ζ)) term from SABR formula."""
    if abs(z) < 1e-8:
        return 1.0
    disc = math.sqrt(max(1.0 - 2.0 * rho * z + z ** 2, 0.0))
    arg = (disc + z - rho) / (1.0 - rho)
    if arg <= 0:
        return 1.0
    return math.log(arg) / z if abs(z) > 1e-12 else 1.0


def _calibration_objective(
    params: np.ndarray,
    market_data: list[tuple[float, float]],  # [(strike, market_iv), ...]
    forward: float,
    ttm: float,
    beta: float,
) -> float:
    """RMSE objective + regularisation for scipy.optimize.minimize."""
    alpha, rho, nu = float(params[0]), float(params[1]), float(params[2])

    # Penalty for boundary violations (soft constraint)
    penalty = 0.0
    if not (_ALPHA_BOUNDS[0] <= alpha <= _ALPHA_BOUNDS[1]):
        penalty += 1e6
    if not (_RHO_BOUNDS[0] <= rho <= _RHO_BOUNDS[1]):
        penalty += 1e6
    if not (_NU_BOUNDS[0] <= nu <= _NU_BOUNDS[1]):
        penalty += 1e6
    if penalty > 0:
        return penalty

    sse = 0.0
    for strike, mkt_iv in market_data:
        sabr_iv = _sabr_implied_vol(forward, strike, ttm, alpha, beta, rho, nu)
        diff = sabr_iv - mkt_iv
        sse += diff * diff

    return math.sqrt(sse / max(len(market_data), 1))


class SABRCalibrator:
    """Full SABR smile calibrator using scipy.optimize.

    Calibrates {α, ρ, ν} from market IV observations (strikes near ATM).
    Provides O(1) IV interpolation for any strike after calibration.

    Thread safety: calibrate() may be called from asyncio.to_thread().
    interpolate() is read-only and always thread-safe.

    Usage::

        cal = SABRCalibrator(beta=0.5)
        market_ivs = {560.0: 0.21, 555.0: 0.23, 565.0: 0.20}
        success = cal.calibrate(market_ivs, forward=560.5, ttm=0.002)
        iv_at_558 = cal.interpolate(558.0, 0.002)
    """

    def __init__(
        self,
        beta: float = _BETA,
        calibration_interval: float = _CALIBRATION_INTERVAL,
    ) -> None:
        self.beta = beta
        self._interval = calibration_interval
        self._params: Optional[SABRParams] = None
        self._last_calibrated: float = 0.0

    @property
    def is_calibrated(self) -> bool:
        return self._params is not None and self._params.is_valid

    @property
    def params(self) -> Optional[SABRParams]:
        return self._params

    def should_recalibrate(self) -> bool:
        """True if enough time has passed since last calibration."""
        return (time.monotonic() - self._last_calibrated) >= self._interval

    def calibrate(
        self,
        market_ivs: dict[float, float],    # {strike: implied_vol}
        forward: float,
        ttm: float,
    ) -> bool:
        """Calibrate SABR parameters from market observations.

        Args:
            market_ivs: Dict of {strike: market_implied_vol (decimal)}.
                        Best results with 5+ strikes spanning ATM ± 10 pts.
            forward:    ATM forward price (typically spot for 0DTE).
            ttm:        Time to maturity in years.

        Returns:
            True on successful calibration (RMSE < 1%).
        """
        if not _SCIPY_AVAILABLE:
            logger.warning("[SABRCalibrator] scipy unavailable — using linear skew fallback.")
            self._params = self._linear_skew_fallback(market_ivs, forward)
            return False

        # Filter calibration data to ATM ± window
        data: list[tuple[float, float]] = [
            (k, v) for k, v in market_ivs.items()
            if v > 0 and abs(k - forward) <= _ATM_WINDOW
        ]

        if len(data) < 3:
            logger.warning(
                "[SABRCalibrator] Insufficient market data for SABR (%d points). Need ≥ 3.", len(data)
            )
            self._params = self._linear_skew_fallback(market_ivs, forward)
            return False

        # Initial guess: use ATM IV as alpha, rho=-0.3, nu=0.4
        atm_iv = self._interpolate_atm_iv(market_ivs, forward)
        x0 = np.array([atm_iv, -0.30, 0.40])

        bounds = [_ALPHA_BOUNDS, _RHO_BOUNDS, _NU_BOUNDS]

        try:
            result = minimize(
                fun=_calibration_objective,
                x0=x0,
                args=(data, forward, ttm, self.beta),
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-8},
            )

            alpha, rho, nu = float(result.x[0]), float(result.x[1]), float(result.x[2])
            rmse = float(result.fun)

            self._params = SABRParams(
                alpha=alpha, rho=rho, nu=nu, beta=self.beta,
                forward=forward, ttm=ttm,
                calibration_error=rmse,
                calibrated_at=time.monotonic(),
            )
            self._last_calibrated = time.monotonic()

            if rmse > 0.01:
                logger.warning(
                    "[SABRCalibrator] High calibration RMSE: %.4f (alpha=%.3f rho=%.3f nu=%.3f)",
                    rmse, alpha, rho, nu,
                )
            else:
                logger.info(
                    "[SABRCalibrator] Calibrated: alpha=%.4f rho=%.4f nu=%.4f RMSE=%.5f",
                    alpha, rho, nu, rmse,
                )
            return rmse < 0.01

        except Exception as exc:
            logger.error("[SABRCalibrator] calibration failed: %s", exc)
            self._params = self._linear_skew_fallback(market_ivs, forward)
            return False

    def interpolate(self, strike: float, ttm: float) -> float:
        """O(1) SABR IV query for any strike (must call calibrate first).

        Args:
            strike: Target strike price.
            ttm:    Time to maturity in years.

        Returns:
            SABR-implied volatility (decimal). 0.0 if not calibrated.
        """
        if self._params is None:
            return 0.0
        p = self._params
        return _sabr_implied_vol(p.forward, strike, ttm, p.alpha, p.beta, p.rho, p.nu)

    def calibrate_from_chain(
        self,
        chain: list[dict],
        forward: float,
        ttm: float,
    ) -> bool:
        """Convenience: extract IVs from chain dicts and calibrate.

        Args:
            chain:   List of option entry dicts with 'strike' and 'implied_volatility'.
            forward: Current forward price.
            ttm:     Time to maturity in years.
        """
        market_ivs: dict[float, float] = {}
        for entry in chain:
            k = float(entry.get("strike", 0.0))
            iv = float(entry.get("implied_volatility") or 0.0)
            if k > 0 and iv > 0:
                market_ivs[k] = iv

        return self.calibrate(market_ivs, forward, ttm)

    # ── Private ───────────────────────────────────────────────────────────────

    def _interpolate_atm_iv(self, market_ivs: dict[float, float], forward: float) -> float:
        """Approximate ATM IV from nearest market strikes."""
        if not market_ivs:
            return 0.20
        nearest = min(market_ivs.keys(), key=lambda k: abs(k - forward))
        return market_ivs[nearest]

    def _linear_skew_fallback(
        self, market_ivs: dict[float, float], forward: float
    ) -> SABRParams:
        """Fallback when scipy unavailable: synthesise params from ATM IV."""
        atm_iv = self._interpolate_atm_iv(market_ivs, forward) if market_ivs else 0.20
        return SABRParams(
            alpha=atm_iv, rho=-0.30, nu=0.40, beta=self.beta,
            forward=forward, ttm=0.0,
            calibration_error=float("inf"),
            calibrated_at=time.monotonic(),
        )

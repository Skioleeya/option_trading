"""SABR Calibrator - Rust-first SABR smile calibration."""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from shared_rust.services import calibrate_sabr as _rust_calibrate_sabr  # type: ignore
    from shared_rust.services import sabr_iv as _rust_sabr_iv  # type: ignore
    _RUST_AVAILABLE = True
except (ImportError, AttributeError):
    _rust_calibrate_sabr = None
    _rust_sabr_iv = None
    _RUST_AVAILABLE = False

_BETA: float = 0.5
_ATM_WINDOW: float = 10.0
_CALIBRATION_INTERVAL: float = 120.0
_ALPHA_BOUNDS = (0.001, 5.0)
_RHO_BOUNDS = (-0.999, 0.999)
_NU_BOUNDS = (0.001, 5.0)
_DEFAULT_ALPHA_INIT = 0.20
_DEFAULT_RHO_INIT = -0.30
_DEFAULT_NU_INIT = 0.40
_MAX_ITER = 1000
_TOL = 1e-8


@dataclass
class SABRParams:
    """Calibrated SABR parameters."""

    alpha: float = 0.20
    rho: float = -0.30
    nu: float = 0.40
    beta: float = _BETA
    forward: float = 0.0
    ttm: float = 0.0
    calibration_error: float = float("inf")
    calibrated_at: float = 0.0

    @property
    def is_valid(self) -> bool:
        return self.calibration_error < 0.01


def _log_chi(z: float, rho: float) -> float:
    if abs(z) < 1e-8:
        return 1.0
    disc = math.sqrt(max(1.0 - 2.0 * rho * z + z * z, 0.0))
    arg = (disc + z - rho) / (1.0 - rho)
    if arg <= 0.0:
        return 1.0
    return math.log(arg) / z if abs(z) > 1e-12 else 1.0


def _sabr_implied_vol(
    forward: float,
    strike: float,
    ttm: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
) -> float:
    if ttm <= 0.0 or alpha <= 0.0:
        return 0.0

    F = max(float(forward), 1e-9)
    K = max(float(strike), 1e-9)
    FK_mid = math.sqrt(abs(F * K))
    log_fk = math.log(F / K) if abs(F - K) > 1e-9 else 0.0
    epsilon = abs((F - K) / max(F, 1e-9))

    if epsilon < 1e-4:
        fk_beta = FK_mid ** (1.0 - beta)
        z_a = (
            alpha / fk_beta
            * (
                1.0
                + ((1.0 - beta) ** 2 / 24.0) * (alpha * alpha / FK_mid ** (2.0 - 2.0 * beta))
                + (rho * beta * nu * alpha) / (4.0 * FK_mid ** (1.0 - beta))
                + (2.0 - 3.0 * rho * rho) * nu * nu / 24.0
            )
            * ttm
        )
        return alpha / fk_beta * (1.0 + z_a)

    fk_beta = FK_mid ** (1.0 - beta)
    z = (nu / alpha) * fk_beta * log_fk
    denom = _log_chi(z, rho)
    if abs(denom) < 1e-12:
        denom = 1.0
    z_chi = z / denom

    a_term = alpha / (
        fk_beta
        * (
            1.0
            + ((1.0 - beta) ** 2 / 24.0) * log_fk * log_fk
            + ((1.0 - beta) ** 4 / 1920.0) * log_fk ** 4
        )
    )

    b_term = 1.0 + (
        ((1.0 - beta) ** 2 / 24.0) * (alpha * alpha / FK_mid ** (2.0 - 2.0 * beta))
        + (rho * beta * nu * alpha) / (4.0 * FK_mid ** (1.0 - beta))
        + (2.0 - 3.0 * rho * rho) * nu * nu / 24.0
    ) * ttm

    return a_term * z_chi * b_term


class SABRCalibrator:
    """Rust-first SABR smile calibrator."""

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
        return (time.monotonic() - self._last_calibrated) >= self._interval

    def calibrate(
        self,
        market_ivs: dict[float, float],
        forward: float,
        ttm: float,
    ) -> bool:
        data = sorted(
            (float(k), float(v))
            for k, v in market_ivs.items()
            if float(v) > 0.0 and abs(float(k) - float(forward)) <= _ATM_WINDOW
        )

        if len(data) < 3:
            self._params = self._linear_skew_fallback(market_ivs, float(forward))
            return False

        if not _RUST_AVAILABLE or _rust_calibrate_sabr is None:
            raise RuntimeError("shared_rust.services.calibrate_sabr unavailable")

        alpha_init, rho_init, nu_init = self._initial_guess(market_ivs, float(forward))
        strikes = [strike for strike, _ in data]
        market = [iv for _, iv in data]

        try:
            alpha, rho, nu, residual_mse = _rust_calibrate_sabr(
                strikes,
                market,
                float(forward),
                float(ttm),
                float(self.beta),
                float(alpha_init),
                float(rho_init),
                float(nu_init),
                int(_MAX_ITER),
                float(_TOL),
            )
        except Exception as exc:  # nosec B904 - explicit bridge failure context
            logger.error("[SABRCalibrator] Rust calibration failed: %s", exc)
            raise RuntimeError("Rust SABR calibration failed") from exc

        self._params = SABRParams(
            alpha=float(alpha),
            rho=float(rho),
            nu=float(nu),
            beta=float(self.beta),
            forward=float(forward),
            ttm=float(ttm),
            calibration_error=float(residual_mse),
            calibrated_at=time.monotonic(),
        )
        self._last_calibrated = time.monotonic()

        if residual_mse > 0.01:
            logger.warning(
                "[SABRCalibrator] High calibration MSE: %.6f (alpha=%.4f rho=%.4f nu=%.4f)",
                residual_mse,
                alpha,
                rho,
                nu,
            )
        else:
            logger.info(
                "[SABRCalibrator] Calibrated: alpha=%.4f rho=%.4f nu=%.4f MSE=%.6f",
                alpha,
                rho,
                nu,
                residual_mse,
            )
        return float(residual_mse) < 0.01

    def interpolate(self, strike: float, ttm: float) -> float:
        if self._params is None:
            return 0.0
        if not _RUST_AVAILABLE or _rust_sabr_iv is None:
            raise RuntimeError("shared_rust.services.sabr_iv unavailable")

        p = self._params
        try:
            return float(
                _rust_sabr_iv(
                    float(strike),
                    float(p.forward),
                    float(ttm),
                    float(p.alpha),
                    float(p.beta),
                    float(p.rho),
                    float(p.nu),
                )
            )
        except Exception as exc:  # nosec B904 - explicit bridge failure context
            logger.error("[SABRCalibrator] Rust interpolation failed: %s", exc)
            raise RuntimeError("Rust SABR interpolation failed") from exc

    def calibrate_from_chain(
        self,
        chain: list[dict],
        forward: float,
        ttm: float,
    ) -> bool:
        market_ivs: dict[float, float] = {}
        for entry in chain:
            strike = float(entry.get("strike", 0.0))
            iv = float(entry.get("implied_volatility") or 0.0)
            if strike > 0.0 and iv > 0.0:
                market_ivs[strike] = iv
        return self.calibrate(market_ivs, forward, ttm)

    def _initial_guess(self, market_ivs: dict[float, float], forward: float) -> tuple[float, float, float]:
        if self._params is not None:
            return self._params.alpha, self._params.rho, self._params.nu
        return self._interpolate_atm_iv(market_ivs, forward), _DEFAULT_RHO_INIT, _DEFAULT_NU_INIT

    def _interpolate_atm_iv(self, market_ivs: dict[float, float], forward: float) -> float:
        if not market_ivs:
            return 0.20
        nearest = min(market_ivs.keys(), key=lambda strike: abs(strike - forward))
        return float(market_ivs[nearest])

    def _linear_skew_fallback(self, market_ivs: dict[float, float], forward: float) -> SABRParams:
        atm_iv = self._interpolate_atm_iv(market_ivs, forward) if market_ivs else 0.20
        return SABRParams(
            alpha=atm_iv,
            rho=_DEFAULT_RHO_INIT,
            nu=_DEFAULT_NU_INIT,
            beta=self.beta,
            forward=forward,
            ttm=0.0,
            calibration_error=float("inf"),
            calibrated_at=time.monotonic(),
        )

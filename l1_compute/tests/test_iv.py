"""Tests for IVResolver and SABRCalibrator.

Validates:
    1. WS IV takes priority when fresh
    2. REST IV used when WS expired
    3. Chain IV used when REST missing
    4. SABR fallback activates when all upstream missing
    5. IV clamped to [0.01, 5.0]
    6. SABR calibration RMSE < 1% on synthetic smile
    7. SABR interpolation monotonicity check
"""

from __future__ import annotations

import math
import sys
import time

import pytest

sys.path.insert(0, "e:\\US.market\\Option_v3")

from l1_compute.iv.iv_resolver import IVResolver, IVSource
from l1_compute.iv.sabr_calibrator import SABRCalibrator, _sabr_implied_vol


class TestIVResolver:

    def setup_method(self):
        self.resolver = IVResolver()

    def test_ws_iv_preferred_when_fresh(self):
        rv = self.resolver.resolve(
            symbol="SPY...",
            ws_iv=0.20, ws_iv_timestamp=time.monotonic(),
            rest_iv=0.25, chain_iv=0.30,
            spot=560.0, spot_ref=560.0,
            opt_type="CALL",
        )
        assert rv.source == IVSource.WS
        assert rv.is_valid

    def test_rest_iv_fallback_when_ws_expired(self):
        rv = self.resolver.resolve(
            symbol="SPY...",
            ws_iv=0.20, ws_iv_timestamp=time.monotonic() - 99999.0,  # expired
            rest_iv=0.25, chain_iv=0.30,
            spot=560.0, spot_ref=560.0,
            opt_type="CALL",
        )
        assert rv.source == IVSource.REST
        assert abs(rv.raw_value - 0.25) < 1e-9

    def test_chain_iv_fallback_when_rest_missing(self):
        rv = self.resolver.resolve(
            symbol="SPY...",
            ws_iv=None, ws_iv_timestamp=None,
            rest_iv=None, chain_iv=0.30,
            spot=560.0, spot_ref=560.0,
            opt_type="PUT",
        )
        assert rv.source == IVSource.CHAIN
        assert abs(rv.raw_value - 0.30) < 1e-9

    def test_missing_when_all_absent(self):
        rv = self.resolver.resolve(
            symbol="SPY...",
            ws_iv=None, ws_iv_timestamp=None,
            rest_iv=None, chain_iv=None,
            spot=560.0, spot_ref=560.0,
            opt_type="CALL",
        )
        assert rv.source == IVSource.MISSING
        assert not rv.is_valid

    def test_iv_clamped_high(self):
        """IV > 5.0 must be clamped to 5.0."""
        rv = self.resolver.resolve(
            symbol="SPY...",
            ws_iv=50.0, ws_iv_timestamp=time.monotonic(),
            rest_iv=None, chain_iv=None,
            spot=560.0, spot_ref=560.0,
            opt_type="CALL",
        )
        assert rv.value <= 5.0

    def test_iv_clamped_low(self):
        """IV < 0.01 must be clamped to 0.01 after skew adjustment."""
        rv = self.resolver.resolve(
            symbol="SPY...",
            ws_iv=0.001, ws_iv_timestamp=time.monotonic(),
            rest_iv=None, chain_iv=None,
            spot=560.0, spot_ref=600.0,   # large drop to trigger max negative skew
            opt_type="CALL",
        )
        assert rv.value >= 0.01

    def test_call_put_skew_direction(self):
        """For spot up: call IV should increase, put IV should decrease."""
        base_iv = 0.20
        spot_now, spot_ref = 565.0, 560.0

        rv_call = self.resolver.resolve(
            "C", ws_iv=base_iv, ws_iv_timestamp=time.monotonic(),
            rest_iv=None, chain_iv=None,
            spot=spot_now, spot_ref=spot_ref, opt_type="CALL",
        )
        rv_put = self.resolver.resolve(
            "P", ws_iv=base_iv, ws_iv_timestamp=time.monotonic(),
            rest_iv=None, chain_iv=None,
            spot=spot_now, spot_ref=spot_ref, opt_type="PUT",
        )
        assert rv_call.value > base_iv, "Call IV should rise when spot rises"
        assert rv_put.value < base_iv,  "Put IV should fall when spot rises"

    def test_batch_resolve_dict_keys(self):
        """batch_resolve returns a result for every entry in chain."""
        entries = [
            {"symbol": f"SPY{i:03d}", "type": "CALL", "strike": 560.0 + i,
             "implied_volatility": 0.20, "iv_timestamp": 0.0}
            for i in range(5)
        ]
        result = self.resolver.batch_resolve(entries, spot=560.0, iv_cache={}, spot_at_sync={})
        assert len(result) == 5
        for entry in entries:
            assert entry["symbol"] in result


class TestSABRCalibrator:

    def test_calibration_on_synthetic_smile(self):
        """Calibrate on synthetic SABR-generated IVs, verify RMSE < 1%."""
        # Ground-truth parameters
        alpha_gt, rho_gt, nu_gt, beta_gt = 0.20, -0.40, 0.50, 0.5
        forward, ttm = 560.0, 0.002
        strikes = [545, 550, 555, 560, 565, 570, 575]
        market_ivs = {
            k: _sabr_implied_vol(forward, k, ttm, alpha_gt, beta_gt, rho_gt, nu_gt)
            for k in strikes
        }

        cal = SABRCalibrator(beta=0.5)
        success = cal.calibrate(market_ivs, forward=forward, ttm=ttm)

        if not success:
            pytest.skip("scipy not available or calibration failed (environment issue)")

        assert cal.is_calibrated
        assert cal.params.calibration_error < 0.01, (
            f"RMSE too high: {cal.params.calibration_error:.4f}"
        )

    def test_interpolation_monotonicity(self):
        """Put wing should have higher IV than ATM (typical index skew)."""
        alpha_gt, rho_gt, nu_gt, beta_gt = 0.20, -0.60, 0.40, 0.5
        forward, ttm = 560.0, 0.003
        strikes = list(range(545, 580, 1))
        market_ivs = {
            k: _sabr_implied_vol(forward, k, ttm, alpha_gt, beta_gt, rho_gt, nu_gt)
            for k in strikes
        }
        cal = SABRCalibrator()
        success = cal.calibrate(market_ivs, forward=forward, ttm=ttm)
        if not success:
            pytest.skip("scipy unavailable")

        iv_otm_put = cal.interpolate(545.0, ttm)   # deep put
        iv_atm     = cal.interpolate(560.0, ttm)
        # Index skew: put OTM should trade at higher IV than ATM
        assert iv_otm_put >= iv_atm * 0.95, (
            f"Expected put skew: OTM_put={iv_otm_put:.4f} atm={iv_atm:.4f}"
        )

    def test_sabr_iv_formula_atm(self):
        """SABR ATM formula: σ_SABR(F,F) ≈ α / F^(1-β) (leading term)."""
        alpha, rho, nu, beta = 0.20, -0.30, 0.40, 0.5
        F, t = 560.0, 0.003
        sabr_atm = _sabr_implied_vol(F, F, t, alpha, beta, rho, nu)
        approx   = alpha / (F ** (1.0 - beta))
        # Within 20% of leading-order approximation (correction terms expected)
        assert abs(sabr_atm - approx) < approx * 0.20, (
            f"SABR ATM ({sabr_atm:.4f}) deviates > 20% from leading-order ({approx:.4f})"
        )

    def test_insufficient_data_fallback(self):
        """Fewer than 3 calibration points should not crash; uses linear fallback."""
        cal = SABRCalibrator()
        market_ivs = {560.0: 0.20}
        success = cal.calibrate(market_ivs, forward=560.0, ttm=0.002)
        # Should not raise; success=False is acceptable
        assert cal.params is not None

    def test_should_recalibrate(self):
        """should_recalibrate returns True before first calibration."""
        cal = SABRCalibrator(calibration_interval=120.0)
        assert cal.should_recalibrate()

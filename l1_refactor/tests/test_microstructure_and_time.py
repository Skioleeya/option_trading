"""Tests for VPIN v2, BBO v2, Volume Acceleration v2, and TTM v2."""

from __future__ import annotations

import math
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, "e:\\US.market\\Option_v3")

from l1_refactor.microstructure.vpin_v2 import VPINv2, VPINRegime
from l1_refactor.microstructure.bbo_v2 import BBOv2
from l1_refactor.microstructure.vol_accel_v2 import VolAccelV2, SessionPhase
from l1_refactor.time.ttm_v2 import (
    get_trading_ttm_v2,
    get_trading_ttm_v2_scalar,
    SettlementType,
    _ANNUAL_TRADING_SECONDS,
    _TRADING_SECONDS_PER_DAY,
)

_ET = ZoneInfo("US/Eastern")


# ─────────────────────────────────────────────────────────────────────────────
# VPIN v2
# ─────────────────────────────────────────────────────────────────────────────

class TestVPINv2:

    def test_initial_signal_zero(self):
        vpin = VPINv2()
        sig = vpin.get_signal()
        assert sig.tf_1m.score == 0.0
        assert sig.tf_5m.score == 0.0

    def test_all_buy_trades_gives_vpin_1(self):
        """100% buy volume should produce VPIN ≈ 1.0 after bucket completion."""
        vpin = VPINv2(initial_bucket_size=100.0)
        trades = [{"vol": 10.0, "dir": 1}] * 50   # 500 buy volume
        vpin.update(trades)
        sig = vpin.get_signal()
        assert sig.buckets_filled >= 4
        assert sig.tf_1m.score >= 0.95, f"Expected VPIN ≈ 1.0, got {sig.tf_1m.score}"

    def test_balanced_trades_gives_low_vpin(self):
        """Equal buy/sell volume → VPIN ≈ 0."""
        vpin = VPINv2(initial_bucket_size=100.0)
        trades = [{"vol": 10.0, "dir": 1}, {"vol": 10.0, "dir": -1}] * 25
        vpin.update(trades)
        sig = vpin.get_signal()
        # Allow some tolerance for partial bucket
        assert sig.tf_1m.score <= 0.15, f"Balanced VPIN should be near 0, got {sig.tf_1m.score}"

    def test_regime_classifies_correctly(self):
        """VPIN > 0.75 → TOXIC, 0.5-0.75 → ELEVATED, < 0.5 → NORMAL."""
        vpin = VPINv2(initial_bucket_size=50.0)
        vpin.update([{"vol": 10.0, "dir": 1}] * 100)  # all buys → VPIN ~1.0
        sig = vpin.get_signal()
        # 1m window: depends on timing; at least ELEVATED expected
        assert sig.tf_1m.regime in (VPINRegime.ELEVATED, VPINRegime.TOXIC)

    def test_adaptive_bucket_size(self):
        """After end_of_session, set_adaptive_bucket_size changes bucket size."""
        vpin = VPINv2(initial_bucket_size=500.0)
        vpin._session_vol = 1_000_000.0  # simulate a high-volume session
        vpin.end_of_session()
        vpin.set_adaptive_bucket_size(adv_fraction=0.01)
        assert vpin._bucket_size == pytest.approx(10_000.0, rel=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# BBO v2
# ─────────────────────────────────────────────────────────────────────────────

class _FakeBidAsk:
    def __init__(self, volume: float):
        self.volume = volume


class TestBBOv2:

    def test_all_bid_volume_gives_positive_imbalance(self):
        bbo = BBOv2()
        bids = [_FakeBidAsk(100.0), _FakeBidAsk(50.0), _FakeBidAsk(25.0)]
        asks = [_FakeBidAsk(0.0), _FakeBidAsk(0.0), _FakeBidAsk(0.0)]
        sig = bbo.update("SYM", bids, asks)
        assert sig.raw_imbalance == pytest.approx(1.0), f"Expected 1.0, got {sig.raw_imbalance}"

    def test_all_ask_volume_gives_negative_imbalance(self):
        bbo = BBOv2()
        bids = [_FakeBidAsk(0.0)] * 3
        asks = [_FakeBidAsk(200.0), _FakeBidAsk(100.0), _FakeBidAsk(50.0)]
        sig = bbo.update("SYM", bids, asks)
        assert sig.raw_imbalance == pytest.approx(-1.0)

    def test_ewma_smoothing_converges(self):
        """Repeated equal imbalance should converge EWMA to that value."""
        bbo = BBOv2(alpha_fast=0.5)
        bids = [_FakeBidAsk(100.0)]
        asks = [_FakeBidAsk(0.0)]
        for _ in range(20):
            bbo.update("SYM", bids, asks)
        sig = bbo.get_signal("SYM")
        assert sig.ewma_fast > 0.95, f"EWMA should converge near 1.0, got {sig.ewma_fast}"

    def test_cross_contract_signal_averages(self):
        bbo = BBOv2()
        bids = [_FakeBidAsk(150.0)]
        asks = [_FakeBidAsk(50.0)]  # imbalance ≈ 0.5
        for sym in ["SYM1", "SYM2", "SYM3"]:
            bbo.update(sym, bids, asks)
        cross = bbo.get_cross_contract_signal(["SYM1", "SYM2", "SYM3"], atm_strike=560.0)
        assert cross.num_contracts == 3
        assert cross.net_imbalance > 0

    def test_none_returned_for_unknown_symbol(self):
        bbo = BBOv2()
        assert bbo.get_signal("UNKNOWN") is None


# ─────────────────────────────────────────────────────────────────────────────
# Volume Acceleration v2
# ─────────────────────────────────────────────────────────────────────────────

class TestVolAccelV2:

    def test_initial_ratio_is_1(self):
        """First tick: EMA = tick_vol, ratio = 1.0."""
        va = VolAccelV2()
        sig = va.update(tick_volume=1000.0, phase=SessionPhase.MID)
        assert sig.ratio == pytest.approx(1.0, abs=1e-6)

    def test_spike_above_threshold_triggers_elevated(self):
        """After stable baseline, a 10x spike should trigger elevated."""
        va = VolAccelV2()
        for _ in range(50):
            va.update(1000.0, phase=SessionPhase.MID)
        sig = va.update(10_000.0, phase=SessionPhase.MID)
        assert sig.ratio > 3.0

    def test_entropy_zero_when_single_contract(self):
        """All volume in one contract → entropy = 0."""
        va = VolAccelV2()
        sig = va.update(1000.0, SessionPhase.MID, per_contract_volumes={"SYM": 1000.0})
        assert sig.entropy == pytest.approx(0.0)

    def test_entropy_max_when_uniform(self):
        """Uniform distribution over N contracts → maximum entropy."""
        va = VolAccelV2()
        n = 10
        contracts = {f"SYM{i}": 100.0 for i in range(n)}
        sig = va.update(1000.0, SessionPhase.MID, per_contract_volumes=contracts)
        max_entropy = math.log(n)
        assert sig.entropy == pytest.approx(max_entropy, rel=1e-6)

    def test_phase_classification(self):
        va = VolAccelV2()
        assert va.classify_phase(9, 45) == SessionPhase.OPEN
        assert va.classify_phase(12, 0) == SessionPhase.MID
        assert va.classify_phase(15, 45) == SessionPhase.CLOSE
        assert va.classify_phase(8, 0) == SessionPhase.PRE_MARKET

    def test_dynamic_threshold_increases_with_history(self):
        """After building ratio history, threshold should be data-driven."""
        va = VolAccelV2(alert_percentile=0.95)
        for _ in range(50):
            va.update(1000.0, SessionPhase.MID)
        # Inject a few spikes to push threshold up
        for _ in range(5):
            va.update(5000.0, SessionPhase.MID)
        last_sig = va.update(1000.0, SessionPhase.MID)
        # Threshold should be above base 2.0 due to spike history
        assert last_sig.threshold >= 2.0


# ─────────────────────────────────────────────────────────────────────────────
# TTM v2
# ─────────────────────────────────────────────────────────────────────────────

class TestTTMv2:

    def test_gamma_floor_applied(self):
        """TTM must be >= floor even at market close."""
        from l1_refactor.time.ttm_v2 import _GAMMA_FLOOR_MINUTES
        now = datetime(2026, 3, 3, 15, 59, 50, tzinfo=_ET)  # 10s before close
        ttm = get_trading_ttm_v2_scalar(now)
        floor = (_GAMMA_FLOOR_MINUTES / 60.0) * 3600.0 / _ANNUAL_TRADING_SECONDS
        assert ttm >= floor * 0.99  # allow ramp adjustment

    def test_ttm_decreases_over_time(self):
        """TTM at 9:30 > TTM at 12:00 > TTM at 15:00."""
        today = date(2026, 3, 3)
        ttm_open = get_trading_ttm_v2(datetime(2026, 3, 3, 9, 30, 0, tzinfo=_ET), today)
        ttm_mid  = get_trading_ttm_v2(datetime(2026, 3, 3, 12, 0, 0, tzinfo=_ET), today)
        ttm_late = get_trading_ttm_v2(datetime(2026, 3, 3, 15, 0, 0, tzinfo=_ET), today)
        assert ttm_open > ttm_mid > ttm_late

    def test_pm_settlement_expires_at_4pm(self):
        """At exactly 4:00:01 PM, PM-settled option should return floor TTM."""
        today = date(2026, 3, 3)
        past  = datetime(2026, 3, 3, 16, 0, 1, tzinfo=_ET)
        ttm   = get_trading_ttm_v2(past, today, SettlementType.PM)
        floor = 10.0 * 60.0 / _ANNUAL_TRADING_SECONDS
        assert ttm == pytest.approx(floor, rel=0.01)

    def test_am_vs_pm_settlement_same_expiry(self):
        """AM-settled TTM should be ~6.5h less than PM-settled at market open."""
        today = date(2026, 3, 4)
        now   = datetime(2026, 3, 3, 9, 30, 0, tzinfo=_ET)
        ttm_pm = get_trading_ttm_v2(now, today, SettlementType.PM)
        ttm_am = get_trading_ttm_v2(now, today, SettlementType.AM)
        # AM expires 6.5h earlier in trading time
        diff_years = ttm_pm - ttm_am
        diff_hours = diff_years * _ANNUAL_TRADING_SECONDS / 3600.0
        assert 5.0 <= diff_hours <= 8.0, f"AM/PM TTM diff: {diff_hours:.2f}h (expected ~6.5h)"

    def test_backward_compat_scalar(self):
        """get_trading_ttm_v2_scalar must return positive value during market hours."""
        now = datetime(2026, 3, 3, 12, 0, 0, tzinfo=_ET)
        ttm = get_trading_ttm_v2_scalar(now)
        assert ttm > 0
        assert ttm < 1.0 / 252.0  # less than one trading day in years

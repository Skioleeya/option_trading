"""VPIN v2 — Multi-bucket multi-frequency Volume-Synchronized PIN.

Enhancements over DepthEngine (v1):
    1. Adaptive bucket size (ADV-percentile based, not fixed)
    2. Three output frequencies: 1min / 5min / 15min
    3. Regime classification: NORMAL / ELEVATED / TOXIC
    4. Confidence score per frequency
    5. ndm_rust bridge interface reserved (Python implementation active)

Architecture:
    Each trade tick is classified (buy/sell/neutral) and accumulated
    into a rolling bucket. When a bucket fills, the VPIN score is
    computed as |buy_vol - sell_vol| / total_vol.

References:
    Easley, López de Prado, O'Hara (2012), "Flow Toxicity and Liquidity
    in a High-Frequency World", RFS 25(5):1457-1493.
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# ── Rust bridge (Phase 2) ────────────────────────────────────────
try:
    import l1_rust as _rust  # type: ignore
    logger.info("[VPINv2] l1_rust native extension loaded for AVX-512 SIMD.")
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────
_DEFAULT_BUCKET_SIZE: float = 500.0
_TIMEFRAMES_SECONDS: dict[str, int] = {"1m": 60, "5m": 300, "15m": 900}
_REGIME_THRESHOLDS = {"NORMAL": 0.0, "ELEVATED": 0.5, "TOXIC": 0.75}


class VPINRegime(str, Enum):
    NORMAL   = "NORMAL"
    ELEVATED = "ELEVATED"
    TOXIC    = "TOXIC"


@dataclass
class VPINTimeframe:
    score: float = 0.0
    regime: VPINRegime = VPINRegime.NORMAL
    confidence: float = 0.0
    directional_vol: float = 0.0
    total_vol: float = 0.0


@dataclass
class VPINSignal:
    """Output of VPINv2 — three-frequency VPIN snapshot."""
    tf_1m:  VPINTimeframe = field(default_factory=VPINTimeframe)
    tf_5m:  VPINTimeframe = field(default_factory=VPINTimeframe)
    tf_15m: VPINTimeframe = field(default_factory=VPINTimeframe)
    bucket_size: float = _DEFAULT_BUCKET_SIZE
    buckets_filled: int = 0

    @property
    def composite_score(self) -> float:
        """Weighted composite: 1m=50%, 5m=30%, 15m=20%."""
        return (
            0.50 * self.tf_1m.score
            + 0.30 * self.tf_5m.score
            + 0.20 * self.tf_15m.score
        )


@dataclass
class _BucketState:
    """Internal bucket accumulation state."""
    buy_vol: float = 0.0
    sell_vol: float = 0.0
    total_vol: float = 0.0

    def fill_fraction(self, threshold: float) -> float:
        return self.total_vol / max(threshold, 1.0)

    def vpin(self) -> float:
        if self.total_vol <= 0:
            return 0.0
        return abs(self.buy_vol - self.sell_vol) / self.total_vol

    def reset(self) -> None:
        self.buy_vol = self.sell_vol = self.total_vol = 0.0


@dataclass
class _CompletedBucket:
    vpin_score: float
    timestamp: float   # time.monotonic()


class VPINv2:
    """Multi-bucket multi-frequency VPIN calculator.

    One instance per tracked symbol. Call update() on each trade tick.

    ADV-Adaptive Bucket Size:
        bucket_size = adv_daily * adv_percentile_fraction
        (defaults to 500 until ADV history is populated)

    ndm_rust Bridge (Phase 2):
        When _RUST_AVAILABLE, update() will delegate the inner bucket
        loop to ndm_rust.update_vpin_v2() for AVX-512 SIMD acceleration.

    Usage::

        vpin = VPINv2()
        vpin.update(trades=[{"vol": 100, "dir": 1}, ...])
        sig = vpin.get_signal()
    """

    def __init__(
        self,
        initial_bucket_size: float = _DEFAULT_BUCKET_SIZE,
        adv_window: int = 20,                  # ADV rolling window days
    ) -> None:
        self._bucket_size = initial_bucket_size
        self._current = _BucketState()
        self._completed: deque[_CompletedBucket] = deque(maxlen=500)
        self._buckets_filled: int = 0
        # Volume history for adaptive bucket sizing
        self._daily_volumes: deque[float] = deque(maxlen=adv_window)
        self._session_vol: float = 0.0

    def update(self, trades: list[dict]) -> None:
        """Process a batch of trade ticks.

        Args:
            trades: List of dicts with keys:
                - 'vol': float — trade size
                - 'dir': int/float — +1=buy, -1=sell, 0=unknown
        """
        if not trades:
            return

        now = time.monotonic()

        if _RUST_AVAILABLE:
            self._update_rust(trades, now)
        else:
            self._update_python(trades, now)

        self._session_vol += sum(t.get("vol", 0.0) for t in trades)

    def set_adaptive_bucket_size(self, adv_fraction: float = 0.01) -> None:
        """Adjust bucket size based on ADV percentile.

        Args:
            adv_fraction: Fraction of daily average volume per bucket.
                          E.g. 0.01 = 1% of ADV.
        """
        if self._daily_volumes:
            adv = sum(self._daily_volumes) / len(self._daily_volumes)
            new_size = max(100.0, adv * adv_fraction)
            logger.debug(
                "[VPINv2] Adaptive bucket size: %.1f → %.1f (ADV=%.0f)",
                self._bucket_size, new_size, adv,
            )
            self._bucket_size = new_size

    def end_of_session(self) -> None:
        """Call at market close to record session volume for ADV adaptation."""
        if self._session_vol > 0:
            self._daily_volumes.append(self._session_vol)
        self._session_vol = 0.0

    def get_signal(self) -> VPINSignal:
        """Return current VPIN signal across all three timeframes."""
        now = time.monotonic()
        return VPINSignal(
            tf_1m=self._compute_timeframe(now, _TIMEFRAMES_SECONDS["1m"]),
            tf_5m=self._compute_timeframe(now, _TIMEFRAMES_SECONDS["5m"]),
            tf_15m=self._compute_timeframe(now, _TIMEFRAMES_SECONDS["15m"]),
            bucket_size=self._bucket_size,
            buckets_filled=self._buckets_filled,
        )

    # ── Private ──────────────────────────────────────────────────────────────

    def _update_python(self, trades: list[dict], now: float) -> None:
        for trade in trades:
            vol = max(0.0, float(trade.get("vol", 0.0)))
            if vol <= 0:
                continue
            dir_sign = float(trade.get("dir", 0))
            buy_v  = vol if dir_sign > 0 else 0.0
            sell_v = vol if dir_sign < 0 else 0.0

            self._current.buy_vol   += buy_v
            self._current.sell_vol  += sell_v
            self._current.total_vol += vol

            # Bucket completion check
            while self._current.total_vol >= self._bucket_size:
                score = self._current.vpin()
                self._completed.append(_CompletedBucket(vpin_score=score, timestamp=now))
                self._buckets_filled += 1
                # Roll over excess volume to next bucket
                excess = self._current.total_vol - self._bucket_size
                fraction = excess / max(vol, 1e-9)
                self._current.reset()
                self._current.total_vol = excess
                self._current.buy_vol   = buy_v * fraction
                self._current.sell_vol  = sell_v * fraction

    def _update_rust(self, trades: list[dict], now: float) -> None:
        """Phase 2 Rust bridge — SIMD accelerated execution."""
        trade_tuples = [(float(t.get("vol", 0.0)), float(t.get("dir", 0))) for t in trades]
        
        buy_vol, sell_vol, total_vol, completed_scores = _rust.update_vpin_v2(
            self._current.buy_vol,
            self._current.sell_vol,
            self._current.total_vol,
            self._bucket_size,
            trade_tuples,
        )
        
        self._current.buy_vol = buy_vol
        self._current.sell_vol = sell_vol
        self._current.total_vol = total_vol
        
        for score in completed_scores:
            self._completed.append(_CompletedBucket(vpin_score=score, timestamp=now))
            self._buckets_filled += 1

    def _compute_timeframe(self, now: float, window_seconds: int) -> VPINTimeframe:
        """Compute VPIN for the most recent `window_seconds`."""
        cutoff = now - window_seconds
        relevant = [b for b in self._completed if b.timestamp >= cutoff]

        if not relevant:
            # Use current partial bucket
            score = self._current.vpin()
            conf = self._current.fill_fraction(self._bucket_size) * 0.5
        else:
            scores = [b.vpin_score for b in relevant]
            score = sum(scores) / len(scores)
            conf = min(len(relevant) / 10.0, 1.0)  # 10 complete buckets = full confidence

        regime = self._classify_regime(score)
        return VPINTimeframe(
            score=score,
            regime=regime,
            confidence=conf,
            directional_vol=self._current.buy_vol - self._current.sell_vol,
            total_vol=self._current.total_vol,
        )

    @staticmethod
    def _classify_regime(score: float) -> VPINRegime:
        if score >= _REGIME_THRESHOLDS["TOXIC"]:
            return VPINRegime.TOXIC
        if score >= _REGIME_THRESHOLDS["ELEVATED"]:
            return VPINRegime.ELEVATED
        return VPINRegime.NORMAL

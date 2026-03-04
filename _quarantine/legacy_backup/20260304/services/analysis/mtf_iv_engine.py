"""MTF IV Engine — Volatility Surface Regime Shift Detection (VSRSD).

Academic basis:
    Andersen et al. (2024, Management Science) — "Intraday Option Flow
    and Volatility Surface Dynamics"

    Carr & Wu (2023, JF) — "Term Structure of Variance Risk Premiums"

Algorithm:
    1. Maintain a rolling window of ATM IV per timeframe bucket (1M/5M/15M).
    2. Compute Z-Score of current IV vs window mean/std.
    3. Classify regime per timeframe.
    4. Compute MTF alignment score (how many timeframes agree).

Regime classes:
    BREAKOUT  (Z > +2.0)   → IV spike = directional option buying = BULLISH
    STRESS    (Z < -2.0)   → IV crash = short covering / selling  = BEARISH
    DRIFT     (|Z| 0.5-2)  → mild deviation
    NOISE     (|Z| < 0.5)  → below significance
"""

from __future__ import annotations

import logging
import math
from collections import deque
from statistics import mean, stdev
from typing import Any

logger = logging.getLogger(__name__)

# --- Configuration ---
_WINDOW_SIZES = {"1m": 20, "5m": 12, "15m": 8}   # bars to keep per TF
_Z_BREAKOUT   =  2.0
_Z_STRESS     = -2.0
_Z_DRIFT      =  0.5

_MIN_SAMPLES  = 5   # minimum bars before Z-Score is meaningful


class MTFIVEngine:
    """Rolling ATM IV Z-Score per timeframe, yielding regime + alignment."""

    def __init__(self) -> None:
        # { "1m": deque([iv, ...]), "5m": ..., "15m": ... }
        self._windows: dict[str, deque[float]] = {
            tf: deque(maxlen=_WINDOW_SIZES[tf]) for tf in _WINDOW_SIZES
        }

    # ------------------------------------------------------------------
    def update(self, tf: str, atm_iv: float) -> None:
        """Push a new ATM IV observation into the timeframe window."""
        if tf in self._windows:
            self._windows[tf].append(atm_iv)

    # ------------------------------------------------------------------
    def compute(self, current_iv_map: dict[str, float]) -> dict[str, Any]:
        """Compute regime + alignment from the latest snapshot.

        Args:
            current_iv_map: { "1m": iv_float, "5m": iv_float, "15m": iv_float }
                            If a timeframe has no current IV, use None.

        Returns:
            {
              "timeframes": {
                "1m": { "regime": str, "z": float, "strength": float, "direction": str },
                "5m": ...
                "15m": ...
              },
              "alignment": float,   # 0.0 – 1.0  (fraction of TFs that agree with mode)
              "consensus": str,     # BULLISH / BEARISH / NEUTRAL
              "strength": float     # 0.0 – 1.0 composite
            }
        """
        tf_results: dict[str, dict[str, Any]] = {}

        directions: list[str] = []

        for tf, win in self._windows.items():
            cur_iv = current_iv_map.get(tf)
            if cur_iv is None or len(win) < _MIN_SAMPLES:
                tf_results[tf] = _make_unavailable()
                continue

            mu = mean(win)
            sd = stdev(win) if len(win) > 1 else 0.0

            if sd < 1e-8:
                z = 0.0
            else:
                z = (cur_iv - mu) / sd

            regime, direction = _classify(z)
            # Normalised strength: 0→1, capped at |z|=3
            strength = min(abs(z) / 3.0, 1.0)

            tf_results[tf] = {
                "regime": regime,
                "z": round(z, 3),
                "strength": round(strength, 3),
                "direction": direction,
            }
            directions.append(direction)

        # Consensus vote
        consensus, alignment = _vote(directions)
        composite_strength = round(
            mean([r["strength"] for r in tf_results.values()]), 3
        )

        return {
            "timeframes": tf_results,
            "alignment": round(alignment, 3),
            "consensus": consensus,
            "strength": composite_strength,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _classify(z: float) -> tuple[str, str]:
    """Return (regime, direction)."""
    if z >= _Z_BREAKOUT:
        return "BREAKOUT", "BULLISH"
    if z <= _Z_STRESS:
        return "STRESS", "BEARISH"
    if z >= _Z_DRIFT:
        return "DRIFT_UP", "BULLISH"
    if z <= -_Z_DRIFT:
        return "DRIFT_DN", "BEARISH"
    return "NOISE", "NEUTRAL"


def _vote(directions: list[str]) -> tuple[str, float]:
    """Return dominant consensus and fraction of agreement."""
    if not directions:
        return "NEUTRAL", 0.0
    counts = {d: directions.count(d) for d in set(directions)}
    best = max(counts, key=lambda k: counts[k])
    alignment = counts[best] / len(directions)
    if alignment < 0.5:
        return "NEUTRAL", alignment
    return best, alignment


def _make_unavailable() -> dict[str, Any]:
    return {"regime": "UNAVAILABLE", "z": 0.0, "strength": 0.0, "direction": "NEUTRAL"}

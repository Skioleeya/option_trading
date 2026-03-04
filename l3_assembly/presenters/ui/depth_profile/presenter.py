"""DepthProfile submodule — Presenter.

Converts raw per-strike GEX into structured rows for dumb DOM rendering.
Uses an EMA (Exponential Moving Average) smoother to stabilize bar values
across ticks, preventing visual jitter from minute-to-minute GEX fluctuations.

EMA Execution Tiers (2-tier, no pure-Python fallback):
  1. CuPy GPU  — batches all ~14 strikes into a single GPU kernel.
                 Auto-selected when `cupy` is importable + CUDA device present.
  2. Numba JIT — multi-core parallel EMA via @njit prange.
                 Selected when cupy unavailable but numba installed.

Install GPU path: `pip install cupy-cuda12x` (match your CUDA version).
"""

import logging
import math
from collections import Counter
from typing import Any

import numpy as np

from l3_assembly.presenters.ui.depth_profile import mappings, thresholds

logger = logging.getLogger(__name__)


# ─── Tier 1: CuPy GPU probe ──────────────────────────────────────────────────
try:
    import cupy as cp                         # type: ignore
    _probe = cp.array([1.0], dtype=cp.float64)
    del _probe
    _CUPY_AVAILABLE = True
    logger.info("[DepthProfile EMA] CuPy/CUDA detected — GPU EMA ACTIVE (Tier 1).")
except Exception:
    _CUPY_AVAILABLE = False
    logger.info("[DepthProfile EMA] CuPy unavailable — will use Numba JIT (Tier 2).")


# ─── Tier 2: Numba JIT probe ──────────────────────────────────────────────────
try:
    from numba import njit, prange            # type: ignore
    _NUMBA_AVAILABLE = True
    logger.info("[DepthProfile EMA] Numba detected — JIT EMA enabled (Tier 2).")

    @njit(parallel=True, fastmath=True, cache=True)
    def _ema_numba(
        new_calls: np.ndarray,   # float64[n]
        new_puts:  np.ndarray,   # float64[n]
        prev_calls: np.ndarray,  # float64[n]
        prev_puts:  np.ndarray,  # float64[n]
        alpha: float,
    ):
        """Numba JIT parallel EMA over n strikes (call + put in one pass)."""
        n = len(new_calls)
        out_calls = np.empty(n, dtype=np.float64)
        out_puts  = np.empty(n, dtype=np.float64)
        inv_alpha = 1.0 - alpha
        for i in prange(n):
            out_calls[i] = alpha * new_calls[i] + inv_alpha * prev_calls[i]
            out_puts[i]  = alpha * new_puts[i]  + inv_alpha * prev_puts[i]
        return out_calls, out_puts

except ImportError:
    _NUMBA_AVAILABLE = False
    logger.error(
        "[DepthProfile EMA] CRITICAL: Neither CuPy nor Numba is available. "
        "Install `cupy-cuda12x` or `numba`. EMA smoothing will be DISABLED."
    )


# ─── EMA State (module-level singletons) ─────────────────────────────────────
#
# Alpha controls how quickly the smoother tracks new values.
# 0.30 ≈ 2-3 ticks to reach 75% of a step change.
#
_EMA_ALPHA: float = 0.30

# NumPy arrays that hold the previous smoothed value per-strike slot.
# Sized lazily on first call (when we know n_strikes).
_prev_calls: np.ndarray | None = None
_prev_puts:  np.ndarray | None = None

# PP-L3A: Stable center for strike axis (slow EMA — prevents tick-by-tick flip).
_center_ema: float = 0.0
_CENTER_EMA_ALPHA: float = 0.08

# PP-L3B: Asymmetric rise/fall baseline for normalization.
_ema_max_gex: float = 0.0
_MAX_EMA_ALPHA_RISE: float = 0.80   # fast response to new highs
_MAX_EMA_ALPHA_FALL: float = 0.05   # slow decay when below previous high

# BUG-4 FIX: Track the calendar date the EMA state was last reset.
# On the first tick of a new trading day, all EMA state is flushed to cold-start
# values, preventing prior-day GEX peaks from suppressing new-day bar heights
# when the process runs continuously across midnight.
_current_ema_date: str = ""   # YYYYMMDD; empty = not yet initialised

# Sticky cache — preserves last valid rows across ticks where per_strike_gex is empty
_last_valid_depth: list[dict[str, Any]] = []


# ─── Internal helpers (CPU-side, scalar) ─────────────────────────────────────

def _stable_center(spot: float, spacing: float) -> float:
    """PP-L3A: Strike-snapped center via slow EMA — prevents per-tick axis flips."""
    global _center_ema
    if _center_ema == 0.0:
        _center_ema = spot
    else:
        _center_ema = _CENTER_EMA_ALPHA * spot + (1.0 - _CENTER_EMA_ALPHA) * _center_ema
    return round(round(_center_ema / spacing) * spacing, 2)


def _apply_ema_batch(
    new_calls: np.ndarray,
    new_puts:  np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply EMA across all strikes using the active tier (CuPy → Numba).

    Both tiers operate on the same module-level _prev_calls/_prev_puts arrays,
    updated in-place after each tick for O(1) state management.
    """
    global _prev_calls, _prev_puts

    n = len(new_calls)

    # Cold start: seed prev arrays from the first batch so bars appear immediately.
    if _prev_calls is None or len(_prev_calls) != n:
        _prev_calls = new_calls.copy()
        _prev_puts  = new_puts.copy()
        return new_calls.copy(), new_puts.copy()

    if _CUPY_AVAILABLE:
        # ── Tier 1: CuPy GPU ──────────────────────────────────────────────────
        try:
            cp_new_c  = cp.asarray(new_calls)
            cp_new_p  = cp.asarray(new_puts)
            cp_prev_c = cp.asarray(_prev_calls)
            cp_prev_p = cp.asarray(_prev_puts)
            alpha     = _EMA_ALPHA
            inv_alpha = 1.0 - alpha
            sm_c = alpha * cp_new_c + inv_alpha * cp_prev_c
            sm_p = alpha * cp_new_p + inv_alpha * cp_prev_p
            out_calls = cp.asnumpy(sm_c)
            out_puts  = cp.asnumpy(sm_p)
            _prev_calls = out_calls.copy()
            _prev_puts  = out_puts.copy()
            return out_calls, out_puts
        except Exception as exc:
            logger.warning(
                f"[DepthProfile EMA] CuPy path failed ({exc}), falling back to Numba."
            )

    if _NUMBA_AVAILABLE:
        # ── Tier 2: Numba JIT ─────────────────────────────────────────────────
        out_calls, out_puts = _ema_numba(
            new_calls.astype(np.float64),
            new_puts.astype(np.float64),
            _prev_calls.astype(np.float64),
            _prev_puts.astype(np.float64),
            _EMA_ALPHA,
        )
        _prev_calls = out_calls.copy()
        _prev_puts  = out_puts.copy()
        return out_calls, out_puts

    # Neither tier available — return raw unsmoothed values.
    logger.error("[DepthProfile EMA] No compute tier available — returning raw GEX.")
    return new_calls.copy(), new_puts.copy()


# ─── Presenter ────────────────────────────────────────────────────────────────

class DepthProfilePresenter:

    @classmethod
    def build(
        cls,
        per_strike_gex: list[dict[str, Any]],
        spot: float | None,
        flip_level: float | None,
    ) -> list[dict[str, Any]]:
        """Convert per-strike GEX snapshot to frontend-ready row list.

        Key design decisions:
        1. Generates a *contiguous* strike axis by filling in any missing
           strikes within the visible range with zero-GEX rows.
        2. Applies 2-tier GPU EMA (CuPy → Numba) to every strike's
           call_gex / put_gex before normalizing, so bar widths evolve
           smoothly instead of jumping.
        3. Normalizes against a rolling maximum that decays slowly,
           preventing the entire chart from rescaling when the dominant
           bar briefly drops.
        """
        global _ema_max_gex, _center_ema, _last_valid_depth
        if not per_strike_gex:
            # Sticky: return cached result so frontend doesn't blank during transient gaps
            return _last_valid_depth

        # BUG-4 FIX: Reset all module-level EMA state when the trading date rolls over.
        # Without this, a long-running process carries yesterday's EMA peaks into the
        # new session, causing all bars to appear tiny until the legacy peak decays
        # (which takes ~20+ ticks at _MAX_EMA_ALPHA_FALL=0.05).
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _ZI
        global _prev_calls, _prev_puts, _current_ema_date
        today = _dt.now(_ZI("US/Eastern")).strftime("%Y%m%d")
        if today != _current_ema_date:
            logger.info(f"[DepthProfile EMA] New trading day {today} — resetting EMA state.")
            _prev_calls = None
            _prev_puts = None
            _center_ema = 0.0
            _ema_max_gex = 0.0
            _current_ema_date = today

        # ── Step 1: Build lookup from raw data ────────────────────────────────
        raw_by_strike: dict[float, Any] = {}
        for s in per_strike_gex:
            if hasattr(s, "get"):
                k = s.get("strike", 0)
            else:
                k = getattr(s, "strike", 0)
            if k and k > 0:
                raw_by_strike[round(float(k), 2)] = s

        if not raw_by_strike:
            logger.debug(
                f"[L3 DepthProfile] Returning empty profile. "
                f"per_strike_gex length: {len(per_strike_gex)}, valid strikes found: 0"
            )
            return []

        # ── Step 2: Detect strike spacing ─────────────────────────────────────
        sorted_keys = sorted(raw_by_strike.keys())
        if len(sorted_keys) >= 2:
            gaps = [
                round(sorted_keys[i + 1] - sorted_keys[i], 2)
                for i in range(len(sorted_keys) - 1)
            ]
            spacing = Counter(gaps).most_common(1)[0][0]
        else:
            spacing = 1.0
        spacing = max(spacing, 0.5)

        # ── Step 3: Build contiguous strike axis centered on spot ─────────────
        raw_center = spot if spot is not None else sorted_keys[len(sorted_keys) // 2]
        snapped_center = _stable_center(raw_center, spacing)

        count = thresholds.STRIKE_COUNT
        half  = count // 2
        contiguous_strikes = sorted(
            [round(snapped_center + i * spacing, 2) for i in range(-half, count - half)],
            reverse=True,
        )

        # ── Step 4: Collect raw GEX & auxiliary arrays ────────────────────────
        raw_calls  = np.zeros(count, dtype=np.float64)
        raw_puts   = np.zeros(count, dtype=np.float64)
        raw_tox    = np.zeros(count, dtype=np.float64)
        raw_bbo    = np.zeros(count, dtype=np.float64)

        for idx, strike in enumerate(contiguous_strikes):
            data = raw_by_strike.get(strike)
            if data is None:
                for k in raw_by_strike:
                    if abs(k - strike) <= spacing * 0.5:
                        data = raw_by_strike[k]
                        break

            if hasattr(data, "get"):
                raw_calls[idx] = data.get("call_gex", 0.0) if data else 0.0
                raw_puts[idx]  = data.get("put_gex",  0.0) if data else 0.0
                raw_tox[idx]   = data.get("toxicity_score", 0.0) if data else 0.0
                raw_bbo[idx]   = data.get("bbo_imbalance",  0.0) if data else 0.0
            else:
                raw_calls[idx] = getattr(data, "call_gex",        0.0) if data else 0.0
                raw_puts[idx]  = getattr(data, "put_gex",          0.0) if data else 0.0
                raw_tox[idx]   = getattr(data, "toxicity_score",   0.0) if data else 0.0
                raw_bbo[idx]   = getattr(data, "bbo_imbalance",    0.0) if data else 0.0

        # ── Step 5: GPU-accelerated batch EMA (CuPy → Numba) ─────────────────
        sm_calls, sm_puts = _apply_ema_batch(raw_calls, raw_puts)

        # ── Step 6: Stabilize normalization using asymmetric rise/fall EMA ────
        current_max = float(np.max(np.maximum(np.abs(sm_calls), np.abs(sm_puts))))

        if _ema_max_gex == 0.0:
            _ema_max_gex = current_max if current_max > 0 else 1.0
        elif current_max >= _ema_max_gex:
            _ema_max_gex = _MAX_EMA_ALPHA_RISE * current_max + (1.0 - _MAX_EMA_ALPHA_RISE) * _ema_max_gex
        else:
            _ema_max_gex = _MAX_EMA_ALPHA_FALL * current_max + (1.0 - _MAX_EMA_ALPHA_FALL) * _ema_max_gex

        norm_max = _ema_max_gex if _ema_max_gex > 1e-9 else max(current_max, 1.0)

        # ── Step 7: Build output rows ──────────────────────────────────────────
        rows = []
        for idx, strike in enumerate(contiguous_strikes):
            call_gex = float(sm_calls[idx])
            put_gex  = float(sm_puts[idx])

            is_spot = spot       is not None and abs(strike - spot)       < thresholds.STRIKE_PROXIMITY_THRESHOLD
            is_flip = flip_level is not None and abs(strike - flip_level) < thresholds.STRIKE_PROXIMITY_THRESHOLD

            is_dominant_put  = abs(put_gex)  > abs(call_gex) and abs(put_gex)  > norm_max * thresholds.GEX_DOMINANCE_RATIO
            is_dominant_call = abs(call_gex) > abs(put_gex)  and abs(call_gex) > norm_max * thresholds.GEX_DOMINANCE_RATIO

            if is_spot:
                strike_color = mappings.STRIKE_SPOT_COLOR
            elif is_flip:
                strike_color = mappings.STRIKE_FLIP_COLOR
            else:
                strike_color = mappings.STRIKE_DEFAULT_COLOR

            rows.append({
                "strike":           strike,
                "put_pct":          abs(put_gex)  / norm_max,
                "call_pct":         abs(call_gex) / norm_max,
                "put_color":        mappings.PUT_BAR_COLOR,
                "call_color":       mappings.CALL_BAR_COLOR,
                "put_label_color":  mappings.PUT_LABEL_COLOR,
                "call_label_color": mappings.CALL_LABEL_COLOR,
                "spot_tag_classes": mappings.SPOT_TAG_CLASSES,
                "flip_tag_classes": mappings.FLIP_TAG_CLASSES,
                "is_dominant_put":  is_dominant_put,
                "is_dominant_call": is_dominant_call,
                "is_spot":          is_spot,
                "is_flip":          is_flip,
                "strike_color":     strike_color,
                "toxicity_score":   float(raw_tox[idx]),
                "bbo_imbalance":    float(raw_bbo[idx]),
            })

        _last_valid_depth = rows
        return rows

"""DepthProfile submodule — Presenter.

Converts raw per-strike GEX into structured rows for dumb DOM rendering.
Uses an EMA (Exponential Moving Average) smoother to stabilize bar values
across ticks, preventing visual jitter from minute-to-minute GEX fluctuations.

All colors reference this submodule's own palette.
"""

from collections import Counter
from typing import Any

from app.ui.depth_profile import mappings, thresholds


# ─── EMA Smoother (module-level singleton state) ──────────────────────────────
#
# Alpha controls how quickly the smoother tracks new values.
# Lower alpha = smoother / slower to respond.
# 0.30 = approximately 2-3 update cycles to reach 75% of a step change.
#
_EMA_ALPHA: float = 0.30

# per-strike EMA state: { "call_687.0": 1234.5, "put_687.0": -890.2 }
_ema_state: dict[str, float] = {}

# PP-L3A FIX: Stable center EMA — prevents strike axis from flipping every tick
# when spot oscillates near a 0.5-step boundary.
# Alpha=0.08 means the center drifts ~8% toward new spot each tick, roughly
# needing 12+ ticks of sustained movement before the axis shifts one strike.
_center_ema: float = 0.0
_CENTER_EMA_ALPHA: float = 0.08

# PP-L3B FIX: Asymmetric rise/fall EMA for normalization baseline.
# New highs are tracked quickly (RISE alpha=0.80), but the baseline decays
# slowly (FALL alpha=0.05), so a single GEX spike does not suppress the
# entire chart for 20+ ticks while the EMA slowly bleeds back down.
_ema_max_gex: float = 0.0
_MAX_EMA_ALPHA_RISE: float = 0.80   # fast response to new highs
_MAX_EMA_ALPHA_FALL: float = 0.05   # slow, steady decay when below previous high


def _ema(key: str, new_val: float) -> float:
    """Apply EMA to a named series. Returns smoothed value.

    On a cache miss (new key) we seed from new_val so the first value
    renders immediately rather than fading in from zero.
    """
    prev = _ema_state.get(key, new_val)
    smoothed = _EMA_ALPHA * new_val + (1.0 - _EMA_ALPHA) * prev
    _ema_state[key] = smoothed
    return smoothed


def _stable_center(spot: float, spacing: float) -> float:
    """PP-L3A: Return a strike-snapped center that moves via slow EMA.

    By smoothing spot with a low alpha before snapping to strike grid,
    the axis only shifts when spot has sustained a direction for many
    ticks, eliminating per-tick axis flips near half-step boundaries.
    """
    global _center_ema
    if _center_ema == 0.0:
        # Cold start: seed from spot directly.
        _center_ema = spot
    else:
        _center_ema = _CENTER_EMA_ALPHA * spot + (1.0 - _CENTER_EMA_ALPHA) * _center_ema
    return round(round(_center_ema / spacing) * spacing, 2)


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
        1. Generates a *contiguous* strike axis by filling in any missing strikes
           within the visible range with zero-GEX rows.
        2. Applies EMA smoothing to every strike's call_gex / put_gex before
           normalizing, so the bar widths evolve smoothly instead of jumping.
        3. Normalizes against a rolling maximum that decays slowly, preventing
           the entire chart from rescaling when the dominant bar briefly drops.
        """
        global _ema_max_gex, _center_ema

        if not per_strike_gex:
            return []

        # ── Step 1: Build lookup from raw data ────────────────────────────────
        raw_by_strike: dict[float, Any] = {}
        for s in per_strike_gex:
            # Handle both dicts and objects (Pydantic models)
            if hasattr(s, "get"):
                k = s.get("strike", 0)
            else:
                k = getattr(s, "strike", 0)

            if k and k > 0:
                raw_by_strike[round(float(k), 2)] = s

        if not raw_by_strike:
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
        # PP-L3A FIX: Use stable center EMA to prevent per-tick axis flipping
        # when spot oscillates near a 0.5-step boundary.
        raw_center = spot if spot is not None else sorted_keys[len(sorted_keys) // 2]
        snapped_center = _stable_center(raw_center, spacing)

        # For an even count like 14, we'll have (count/2) items below and (count/2 - 1) above,
        # plus the center item itself if we want it centered as possible.
        # Or more simply: range(-7, 7) for count=14.
        count = thresholds.STRIKE_COUNT
        half = count // 2
        contiguous_strikes = sorted(
            [round(snapped_center + i * spacing, 2) for i in range(-half, count - half)],
            reverse=True,
        )

        # ── Step 4: Apply EMA smoothing to raw GEX values ─────────────────────
        smoothed: dict[float, dict[str, float]] = {}
        for strike in contiguous_strikes:
            data = raw_by_strike.get(strike)
            if data is None:
                for k in raw_by_strike:
                    if abs(k - strike) <= spacing * 0.5:
                        data = raw_by_strike[k]
                        break

            # Handle both dicts and objects
            if hasattr(data, "get"):
                raw_call = data.get("call_gex", 0.0) if data else 0.0
                raw_put  = data.get("put_gex", 0.0)  if data else 0.0
            else:
                raw_call = getattr(data, "call_gex", 0.0) if data else 0.0
                raw_put  = getattr(data, "put_gex", 0.0)  if data else 0.0

            sk = f"{strike}"
            smoothed[strike] = {
                "call_gex": _ema(f"call_{sk}", raw_call),
                "put_gex":  _ema(f"put_{sk}",  raw_put),
            }

        # ── Step 5: Stabilize normalization using asymmetric rise/fall EMA ────
        # PP-L3B FIX: Use different alphas for rising vs falling max so a single
        # GEX spike doesn't suppress the chart for 20+ ticks.
        current_max = max(
            (max(abs(v["call_gex"]), abs(v["put_gex"])) for v in smoothed.values()),
            default=0.0,
        )

        if _ema_max_gex == 0.0:
            # Cold start: seed directly.
            _ema_max_gex = current_max if current_max > 0 else 1.0
        elif current_max >= _ema_max_gex:
            # Rising: track rapidly so bars don't clip when a new dominant strike appears.
            _ema_max_gex = _MAX_EMA_ALPHA_RISE * current_max + (1.0 - _MAX_EMA_ALPHA_RISE) * _ema_max_gex
        else:
            # Falling: decay slowly to prevent chart rescaling thrash after a spike.
            _ema_max_gex = _MAX_EMA_ALPHA_FALL * current_max + (1.0 - _MAX_EMA_ALPHA_FALL) * _ema_max_gex

        # Safety: if still near zero use current max or 1.0
        norm_max = _ema_max_gex if _ema_max_gex > 1e-9 else max(current_max, 1.0)

        # ── Step 6: Build output rows ──────────────────────────────────────────
        rows = []
        for strike in contiguous_strikes:
            call_gex = smoothed[strike]["call_gex"]
            put_gex  = smoothed[strike]["put_gex"]

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
                "strike":             strike,
                "put_pct":            abs(put_gex)  / norm_max,
                "call_pct":           abs(call_gex) / norm_max,
                "put_color":          mappings.PUT_BAR_COLOR,
                "call_color":         mappings.CALL_BAR_COLOR,
                "put_label_color":    mappings.PUT_LABEL_COLOR,
                "call_label_color":   mappings.CALL_LABEL_COLOR,
                "spot_tag_classes":   mappings.SPOT_TAG_CLASSES,
                "flip_tag_classes":   mappings.FLIP_TAG_CLASSES,
                "is_dominant_put":    is_dominant_put,
                "is_dominant_call":   is_dominant_call,
                "is_spot":            is_spot,
                "is_flip":            is_flip,
                "strike_color":       strike_color,
            })

        return rows

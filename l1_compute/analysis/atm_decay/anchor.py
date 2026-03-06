"""Anchor validation and selection logic (no I/O)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import (
    MAX_CAPTURE_CANDIDATES,
    MAX_SPOT_PARITY_STRIKE_GAP,
    MIN_LEG_PRICE,
    SPOT_STABILITY_MAX_RANGE,
    SPOT_STABILITY_MIN_SAMPLES,
    SPOT_STABILITY_WINDOW,
    is_integer_strike,
    is_valid_spot,
    mid_price,
    parse_expiry,
)


def validate_anchor(anchor: dict[str, Any]) -> bool:
    """Validate persisted anchor schema and normalize base_strike."""
    required = {"strike", "call_symbol", "put_symbol", "call_price", "put_price", "timestamp"}
    if not required.issubset(anchor.keys()):
        return False
    strike = anchor["strike"]
    if not isinstance(strike, (int, float)) or not is_integer_strike(float(strike)):
        return False
    if "base_strike" not in anchor:
        anchor["base_strike"] = strike
    if not anchor.get("call_symbol") or not anchor.get("put_symbol"):
        return False
    return True


def record_spot_sample(samples: list[float], spot: float) -> None:
    if not is_valid_spot(spot):
        return
    samples.append(float(spot))
    if len(samples) > SPOT_STABILITY_WINDOW:
        del samples[:-SPOT_STABILITY_WINDOW]


def is_spot_stable_for_lock(samples: list[float]) -> tuple[bool, float | None]:
    """Return (ready, span) for strict opening lock gate."""
    if len(samples) < SPOT_STABILITY_MIN_SAMPLES:
        return False, None
    window = samples[-SPOT_STABILITY_MIN_SAMPLES:]
    span = max(window) - min(window)
    return span <= SPOT_STABILITY_MAX_RANGE, span


def select_opening_anchor(
    chain: list[dict[str, Any]],
    spot: float,
    now: datetime,
    logger,
) -> dict[str, Any] | None:
    """Select and build opening anchor payload when consistency checks pass."""
    if not chain or not is_valid_spot(spot):
        return None

    today_ymd = now.strftime("%y%m%d")
    zero_dte = [opt for opt in chain if parse_expiry(opt.get("symbol", "")) == today_ymd]
    if not zero_dte:
        logger.debug(f"[AtmDecay] No 0DTE contracts in chain ({len(chain)} total) for {today_ymd}")
        return None

    strikes = sorted(
        {opt["strike"] for opt in zero_dte if is_integer_strike(float(opt["strike"]))},
        key=lambda s: abs(s - float(spot)),
    )
    if not strikes:
        logger.debug(f"[AtmDecay] No integer strikes in 0DTE subset ({len(zero_dte)} contracts)")
        return None

    logger.info(
        f"[AtmDecay] 0DTE scan: {len(zero_dte)} contracts, "
        f"{len(strikes)} integer strikes, spot={spot:.2f}, "
        f"nearest strikes={strikes[:5]}"
    )

    by_strike: dict[float, dict[str, Any]] = {}
    for opt in zero_dte:
        strike = opt.get("strike")
        if not isinstance(strike, (int, float)) or not is_integer_strike(float(strike)):
            continue

        strike_f = float(strike)
        state = by_strike.setdefault(
            strike_f,
            {"call_symbol": None, "put_symbol": None, "call_price": None, "put_price": None},
        )
        otype = opt.get("option_type", opt.get("type", "")).upper()
        px = mid_price(opt.get("bid", 0.0), opt.get("ask", 0.0), opt.get("last_price", 0.0))
        if otype in ("CALL", "C") and px >= MIN_LEG_PRICE:
            state["call_symbol"] = opt.get("symbol")
            state["call_price"] = float(px)
        elif otype in ("PUT", "P") and px >= MIN_LEG_PRICE:
            state["put_symbol"] = opt.get("symbol")
            state["put_price"] = float(px)

    tradable = [(strike, legs) for strike, legs in by_strike.items() if legs["call_symbol"] and legs["put_symbol"]]
    if not tradable:
        logger.warning(
            "[AtmDecayTracker] No tradable same-strike C/P pair found "
            "(0DTE=%d, integer_strikes=%d).",
            len(zero_dte),
            len(strikes),
        )
        return None

    spot_nearest_strike = min((s for s, _ in tradable), key=lambda s: abs(s - float(spot)))
    parity_strike = min(
        tradable,
        key=lambda kv: abs(float(kv[1]["call_price"]) - float(kv[1]["put_price"])),
    )[0]

    if abs(spot_nearest_strike - parity_strike) > MAX_SPOT_PARITY_STRIKE_GAP:
        logger.warning(
            "[AtmDecayTracker] Lock gated by spot/parity mismatch: "
            "spot=%.2f spot_nearest=%.2f parity_strike=%.2f gap=%.2f max=%.2f",
            float(spot),
            float(spot_nearest_strike),
            float(parity_strike),
            abs(float(spot_nearest_strike) - float(parity_strike)),
            MAX_SPOT_PARITY_STRIKE_GAP,
        )
        return None

    ranked = sorted(tradable, key=lambda kv: abs(kv[0] - float(spot)))[:MAX_CAPTURE_CANDIDATES]
    candidate, legs = ranked[0]
    return {
        "strike": candidate,
        "base_strike": candidate,
        "call_symbol": legs["call_symbol"],
        "put_symbol": legs["put_symbol"],
        "call_price": legs["call_price"],
        "put_price": legs["put_price"],
        "timestamp": now.isoformat(),
    }


def select_roll_anchor(
    anchor: dict[str, Any],
    chain: list[dict[str, Any]],
    spot: float,
    now: datetime,
) -> tuple[dict[str, Any] | None, bool]:
    """Return (new_anchor_payload, is_same_strike)."""
    if not anchor or not chain or not is_valid_spot(spot):
        return None, False

    today_ymd = now.strftime("%y%m%d")
    zero_dte = [opt for opt in chain if parse_expiry(opt.get("symbol", "")) == today_ymd]
    if not zero_dte:
        return None, False

    strikes = sorted(
        {opt["strike"] for opt in zero_dte if is_integer_strike(float(opt["strike"]))},
        key=lambda s: abs(s - float(spot)),
    )
    if not strikes:
        return None, False

    best_candidate = strikes[0]
    if float(best_candidate) == float(anchor["strike"]):
        return None, True

    new_c_sym = new_p_sym = new_c_px = new_p_px = None
    for opt in zero_dte:
        if abs(float(opt["strike"]) - float(best_candidate)) > 0.01:
            continue
        otype = opt.get("option_type", opt.get("type", "")).upper()
        px = mid_price(opt.get("bid", 0.0), opt.get("ask", 0.0), opt.get("last_price", 0.0))
        if otype in ("CALL", "C") and px >= MIN_LEG_PRICE:
            new_c_sym = opt["symbol"]
            new_c_px = float(px)
        elif otype in ("PUT", "P") and px >= MIN_LEG_PRICE:
            new_p_sym = opt["symbol"]
            new_p_px = float(px)

    if new_c_sym and new_p_sym:
        return {
            "strike": float(best_candidate),
            "base_strike": anchor.get("base_strike", anchor["strike"]),
            "call_symbol": new_c_sym,
            "put_symbol": new_p_sym,
            "call_price": new_c_px,
            "put_price": new_p_px,
            "timestamp": now.isoformat(),
        }, False

    return None, False


def calculate_raw_pct(anchor: dict[str, Any] | None, chain: list[dict[str, Any]]) -> tuple[float, float, float] | None:
    """Calculate the un-stitched raw percent decay for the current anchor."""
    if not anchor:
        return None

    target_call = anchor["call_symbol"]
    target_put = anchor["put_symbol"]
    anchor_c = anchor["call_price"]
    anchor_p = anchor["put_price"]
    anchor_s = anchor_c + anchor_p

    curr_c = curr_p = 0.0
    for opt in chain:
        sym = opt.get("symbol")
        if sym == target_call:
            curr_c = mid_price(opt.get("bid", 0.0), opt.get("ask", 0.0), opt.get("last_price", 0.0))
        elif sym == target_put:
            curr_p = mid_price(opt.get("bid", 0.0), opt.get("ask", 0.0), opt.get("last_price", 0.0))

    if curr_c <= 0 or curr_p <= 0:
        return None

    curr_s = curr_c + curr_p
    c_pct = (curr_c - anchor_c) / anchor_c if anchor_c > 0 else 0.0
    p_pct = (curr_p - anchor_p) / anchor_p if anchor_p > 0 else 0.0
    s_pct = (curr_s - anchor_s) / anchor_s if anchor_s > 0 else 0.0
    return c_pct, p_pct, s_pct

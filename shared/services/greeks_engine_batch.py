from __future__ import annotations

import math
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from shared_rust.services import aggregate_from_greeks as _rust_aggregate_from_greeks  # type: ignore
from shared_rust.services import bsm_batch_numpy_tier as _rust_bsm_batch_numpy_tier  # type: ignore

_TRADING_MINUTES_PER_YEAR = 98_280.0
_MIN_TTM_MINUTES = 10.0


def _get_trading_time_to_maturity(now: datetime) -> float:
    tz = ZoneInfo("US/Eastern")
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
    minutes_remaining = (close_time - now).total_seconds() / 60.0
    return max(_MIN_TTM_MINUTES / _TRADING_MINUTES_PER_YEAR, minutes_remaining / _TRADING_MINUTES_PER_YEAR)


def _skew_adjust_iv(
    cached_iv: float,
    spot_now: float,
    spot_ref: float,
    opt_type: str,
    skew_sensitivity: float = 2.0,
) -> float:
    if spot_ref <= 0 or spot_now <= 0:
        return cached_iv

    log_return = math.log(spot_now / spot_ref)
    is_call = opt_type.upper() in ("CALL", "C")
    delta_iv = skew_sensitivity * log_return if is_call else -skew_sensitivity * log_return
    adjusted_iv = cached_iv + delta_iv
    return max(0.01, min(5.0, adjusted_iv))


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_greeks_batch_sync(
    chain_data: list[dict[str, Any]],
    spot: float,
    iv_cache: dict[str, float],
    spot_at_sync: dict[str, float],
    r: float,
    q: float,
) -> tuple[list[tuple[str, dict[str, float]]], dict[str, Any]]:
    now = datetime.now(ZoneInfo("US/Eastern"))
    t_years = _get_trading_time_to_maturity(now)
    n = len(chain_data)

    agg: dict[str, Any] = {
        "net_gex": 0.0,
        "net_vanna": 0.0,
        "net_charm": 0.0,
        "total_call_gex": 0.0,
        "total_put_gex": 0.0,
        "call_wall": None,
        "put_wall": None,
        "max_call_gex": 0.0,
        "max_put_gex": 0.0,
        "atm_iv": 0.0,
    }
    if n == 0:
        agg["ttm_seconds"] = t_years * (252 * 23400)
        return [], agg

    spots_arr = np.full(n, spot, dtype=np.float64)
    strikes_arr = np.empty(n, dtype=np.float64)
    ivs_arr = np.zeros(n, dtype=np.float64)
    is_call_arr = np.empty(n, dtype=np.bool_)
    adj_ivs = np.zeros(n, dtype=np.float64)
    ois_arr = np.zeros(n, dtype=np.float64)
    mults_arr = np.full(n, 100.0, dtype=np.float64)
    vols_arr = np.zeros(n, dtype=np.float64)

    min_strike_diff = float("inf")

    for idx, entry in enumerate(chain_data):
        symbol = str(entry["symbol"])
        strike = _to_float(entry.get("strike", 0.0))
        opt_type = str(entry.get("type", "CALL")).upper()

        strikes_arr[idx] = strike
        is_call_arr[idx] = opt_type in ("CALL", "C")
        vols_arr[idx] = _to_float(entry.get("volume", 0.0))
        ois_arr[idx] = _to_float(entry.get("open_interest", 0.0))
        mults_arr[idx] = _to_float(entry.get("contract_multiplier", 100.0), 100.0)

        raw_iv = _to_float(iv_cache.get(symbol), 0.0)
        if raw_iv > 0.0:
            spot_ref = _to_float(spot_at_sync.get(symbol, spot), spot)
            adj_iv = _skew_adjust_iv(
                cached_iv=raw_iv,
                spot_now=spot,
                spot_ref=spot_ref,
                opt_type=opt_type,
            )
            ivs_arr[idx] = adj_iv
            adj_ivs[idx] = adj_iv

    otm_call_mask = is_call_arr & (strikes_arr > spot)
    otm_put_mask = ~is_call_arr & (strikes_arr < spot)
    agg["otm_call_vol"] = int(np.sum(vols_arr[otm_call_mask]))
    agg["otm_put_vol"] = int(np.sum(vols_arr[otm_put_mask]))
    agg["total_chain_vol"] = int(np.sum(vols_arr))

    batch = _rust_bsm_batch_numpy_tier(spots_arr, strikes_arr, ivs_arr, t_years, is_call_arr, float(r), float(q))
    if not isinstance(batch, dict):
        raise TypeError("Rust bsm_batch_numpy_tier returned non-dict payload")

    batch_agg = _rust_aggregate_from_greeks(
        gamma=batch["gamma"],
        vanna=batch["vanna"],
        charm=batch["charm"],
        spots=spots_arr,
        strikes=strikes_arr,
        is_call=is_call_arr,
        ivs=ivs_arr,
        t_years=t_years,
        ois=ois_arr,
        mults=mults_arr,
    )
    if not isinstance(batch_agg, dict):
        raise TypeError("Rust aggregate_from_greeks returned non-dict payload")

    results: list[tuple[str, dict[str, float]]] = []
    for idx, entry in enumerate(chain_data):
        if ivs_arr[idx] <= 0:
            continue
        symbol = str(entry["symbol"])
        adj_iv = float(adj_ivs[idx])
        greeks = {
            "delta": float(batch["delta"][idx]),
            "gamma": float(batch["gamma"][idx]),
            "vega": float(batch["vega"][idx]),
            "vanna": float(batch["vanna"][idx]),
            "charm": float(batch["charm"][idx]),
            "theta": float(batch["theta"][idx]),
            "implied_volatility": adj_iv,
        }
        results.append((symbol, greeks))

        if adj_iv > 0:
            diff = abs(_to_float(entry.get("strike", 0.0)) - spot)
            if diff < min_strike_diff:
                min_strike_diff = diff
                agg["atm_iv"] = adj_iv

    agg.update(batch_agg)
    agg["ttm_seconds"] = t_years * (252 * 23400)
    return results, agg

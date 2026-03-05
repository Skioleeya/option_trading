"""P4 — GreeksEngine: Async BSM Greeks Computation Worker.

Extracts the _enrich_chain_with_local_greeks() monster function from
OptionChainBuilder and runs it as an independently schedulable async task.

Key institutional improvements over the original:
  1. CPU-bound Numba/CuPy work moved off the asyncio event loop via
     `asyncio.to_thread()`, preventing WS tick drops during 200+ contract chains.
  2. Results written back through ChainStateStore.apply_greeks() rather than
     direct dict mutation on chain_data references.
  3. OI EMA smoothing delegated to ChainStateStore.apply_oi_smooth().
  4. Spot / IV resolution logic unchanged (PP-1/PP-2 TTL guard preserved).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, TYPE_CHECKING

import numpy as np
from zoneinfo import ZoneInfo

from shared.config import settings
from l1_compute.analysis.bsm import get_trading_time_to_maturity, skew_adjust_iv
from l1_compute.analysis.bsm_fast import compute_greeks_batch

if TYPE_CHECKING:
    from l0_ingest.feeds.chain_state_store import ChainStateStore
    from l0_ingest.feeds.iv_baseline_sync import IVBaselineSync

logger = logging.getLogger(__name__)

# IV 唯一来源：REST API calc_indexes（长桥 WS 长连接不提供 IV）。
# ws_iv_raw / _WS_IV_TTL 已移除 — 在长桥实盘中永远为 None，是死代码。


def _build_greeks_sync(
    chain_data: list[dict[str, Any]],
    spot: float,
    iv_cache: dict[str, float],
    spot_at_sync: dict[str, float],
    t_years: float,
) -> tuple[list[tuple[str, dict[str, float]]], dict[str, Any]]:
    """Pure synchronous BSM batch computation — safe to run in a thread pool.

    Args:
        chain_data:   Snapshot list of option entry dicts.
        spot:         Current SPY spot price.
        iv_cache:     REST IV baseline cache from IVBaselineSync（唯一 IV 来源）。
        spot_at_sync: Per-symbol spot reference at IV sync time.
        t_years:      Time to maturity in years.

    Returns:
        Tuple of:
          - [(symbol, greeks_dict), ...] — one entry per valid chain row.
          - agg dict (net_gex, atm_iv, call_wall, put_wall, …).
    """
    now_mono = time.monotonic()
    n = len(chain_data)

    agg: dict[str, Any] = {
        "net_gex": 0.0, "net_vanna": 0.0, "net_charm": 0.0,
        "total_call_gex": 0.0, "total_put_gex": 0.0,
        "call_wall": None, "put_wall": None,
        "max_call_gex": 0.0, "max_put_gex": 0.0, "atm_iv": 0.0,
    }

    if n == 0:
        return [], agg

    spots_arr   = np.full(n, spot,  dtype=np.float64)
    strikes_arr = np.empty(n,        dtype=np.float64)
    ivs_arr     = np.zeros(n,        dtype=np.float64)
    is_call_arr = np.empty(n,        dtype=np.bool_)
    adj_ivs     = np.zeros(n,        dtype=np.float64)
    ois_arr     = np.zeros(n,        dtype=np.float64)
    mults_arr   = np.full(n, 100.0,  dtype=np.float64)
    vols_arr    = np.zeros(n,        dtype=np.float64)

    min_strike_diff = float("inf")

    for idx, entry in enumerate(chain_data):
        symbol   = entry["symbol"]
        strike   = entry.get("strike", 0.0)
        opt_type = entry.get("type", "CALL").upper()

        strikes_arr[idx] = strike
        is_call_arr[idx] = opt_type in ("CALL", "C")
        vols_arr[idx]    = float(entry.get("volume", 0))

        # OI from cache (ChainStateStore already applied EMA)
        ois_arr[idx] = float(entry.get("open_interest", 0))
        mults_arr[idx] = float(entry.get("contract_multiplier", 100))

        # BUG-2 FIX: 长桥 WS 不提供 IV，REST iv_cache 是唯一来源。
        # 原始 ws_iv_raw / chain_iv 路径已移除（死代码：长桥 WS 实盘中永远为 None）。
        raw_iv = iv_cache.get(symbol)

        if raw_iv and raw_iv > 0:
            spot_ref = spot_at_sync.get(symbol, spot)
            adj_iv   = skew_adjust_iv(
                cached_iv=raw_iv,
                spot_now=spot,
                spot_ref=spot_ref,
                opt_type=opt_type,
            )
            ivs_arr[idx]  = adj_iv
            adj_ivs[idx]  = adj_iv

    # Vectorized OTM volume aggregation
    otm_call_mask = is_call_arr & (strikes_arr > spot)
    otm_put_mask  = ~is_call_arr & (strikes_arr < spot)
    agg["otm_call_vol"]    = int(np.sum(vols_arr[otm_call_mask]))
    agg["otm_put_vol"]     = int(np.sum(vols_arr[otm_put_mask]))
    agg["total_chain_vol"] = int(np.sum(vols_arr))

    # Batch BSM (GPU → Numba → NumPy)
    batch, batch_agg = compute_greeks_batch(
        spots_arr, strikes_arr, ivs_arr, t_years, is_call_arr,
        r=settings.risk_free_rate,
        q=settings.bsm_dividend_yield,
        ois=ois_arr,
        mults=mults_arr,
    )

    # Build per-symbol greeks list + ATM IV tracking
    results: list[tuple[str, dict[str, float]]] = []
    for idx, entry in enumerate(chain_data):
        if ivs_arr[idx] <= 0:
            continue
        symbol = entry["symbol"]
        adj_iv = adj_ivs[idx]
        greeks = {
            "delta":   float(batch["delta"][idx]),
            "gamma":   float(batch["gamma"][idx]),
            "vega":    float(batch["vega"][idx]),
            "vanna":   float(batch["vanna"][idx]),
            "charm":   float(batch["charm"][idx]),
            "theta":   float(batch["theta"][idx]),
            "implied_volatility": adj_iv,
        }
        results.append((symbol, greeks))

        if adj_iv > 0:
            diff = abs(entry.get("strike", 0.0) - spot)
            if diff < min_strike_diff:
                min_strike_diff = diff
                agg["atm_iv"] = adj_iv

    if batch_agg:
        agg.update(batch_agg)

    return results, agg


class GreeksEngine:
    """Async wrapper around the synchronous BSM batch computation.

    Decoupled from OptionChainBuilder: receives a chain snapshot from
    ChainStateStore, offloads CPU work to a thread pool, then writes
    results back through ChainStateStore.apply_greeks().
    """

    def __init__(
        self,
        state_store: "ChainStateStore",
        iv_sync: "IVBaselineSync",
    ) -> None:
        self._store = state_store
        self._iv_sync = iv_sync

    async def enrich(
        self,
        chain_snapshot: list[dict[str, Any]],
        spot: float,
    ) -> dict[str, Any]:
        """Compute BSM Greeks for the entire chain, non-blocking.

        Args:
            chain_snapshot: Output of ChainStateStore.get_snapshot().
            spot:           Current SPY spot price.

        Returns:
            Aggregate Greeks dict (net_gex, atm_iv, call_wall, put_wall, …).
        """
        import asyncio

        if not chain_snapshot or spot <= 0:
            return {}

        now     = datetime.now(ZoneInfo("US/Eastern"))
        t_years = get_trading_time_to_maturity(now)

        iv_cache    = self._iv_sync.iv_cache
        spot_at_sync = self._iv_sync.spot_at_sync

        # Offload CPU-bound work — keeps asyncio loop free to process WS ticks
        results, agg = await asyncio.to_thread(
            _build_greeks_sync,
            chain_snapshot,
            spot,
            iv_cache,
            spot_at_sync,
            t_years,
        )

        # Write results back via the store's controlled write point
        for symbol, greeks in results:
            self._store.apply_greeks(symbol, greeks)

        return agg

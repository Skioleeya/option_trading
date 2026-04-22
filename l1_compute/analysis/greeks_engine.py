"""P4 — GreeksEngine: Async BSM Greeks Computation Worker.

Extracts the _enrich_chain_with_local_greeks() monster function from
OptionChainBuilder and runs it as an independently schedulable async task.

Key production improvements over the original:
  1. BSM batch marshalling and Rust owner dispatch moved off the asyncio event loop via
     `asyncio.to_thread()`, preventing WS tick drops during 200+ contract chains.
  2. Results written back through ChainStateStore.apply_greeks() rather than
     direct dict mutation on chain_data references.
  3. OI EMA smoothing delegated to ChainStateStore.apply_oi_smooth().
  4. Spot / IV resolution logic unchanged (PP-1/PP-2 TTL guard preserved).
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from shared.config import settings
from shared.services.greeks_engine_batch import build_greeks_batch_sync

if TYPE_CHECKING:
    from shared_rust.services_l0_support import MVCCChainStateStore as ChainStateStore
    from shared.services.l0_runtime.services.sync import IVBaselineSync

logger = logging.getLogger(__name__)


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

        iv_cache    = self._iv_sync.iv_cache
        spot_at_sync = self._iv_sync.spot_at_sync

        # Offload batch marshalling + Rust owner call off the event loop.
        results, agg = await asyncio.to_thread(
            build_greeks_batch_sync,
            chain_snapshot,
            spot,
            iv_cache,
            spot_at_sync,
            settings.risk_free_rate,
            settings.bsm_dividend_yield,
        )

        # Write results back via the store's controlled write point
        for symbol, greeks in results:
            self._store.apply_greeks(symbol, greeks)

        return agg

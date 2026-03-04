"""BBO v2 — Multi-layer L2 depth weighted BBO imbalance.

Improvements over DepthEngine.update_depth (v1):
    1. Top-5 price levels weighted imbalance (vs Top-1)
    2. EWMA time-weighting: distinguish transient vs persistent imbalance
    3. Cross-contract ATM ± 3 point aggregation
    4. rust_kernel bridge interface reserved for Phase 2

Price-level weighting: inversely proportional to distance from BBO.
    weight_i = 1 / (1 + i)   where i = level index (0=best, 4=5th level)

Persistence signal: EWMA_imbalance tracks structural order book lean.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import l1_rust as _rust  # type: ignore
    logger.info("[BBOv2] l1_rust native extension loaded for branchless SIMD.")
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

# EWMA alpha for imbalance smoothing
_EWMA_ALPHA_FAST: float = 0.30    # fast: captures short-term pressure
_EWMA_ALPHA_SLOW: float = 0.05    # slow: persistent lean / structural
# Price level weights (top-5)
_LEVEL_WEIGHTS = [1.0, 0.5, 0.333, 0.25, 0.20]


@dataclass
class BBOSignal:
    """BBO imbalance signal per symbol."""
    symbol: str
    raw_imbalance: float         # instant snapshot [-1, +1]
    ewma_fast: float             # fast EWMA (transient pressure)
    ewma_slow: float             # slow EWMA (structural lean)
    persistence: float           # |ewma_slow| (higher = more persistent)
    depth_levels_used: int       # how many price levels were available
    timestamp: float             # time.monotonic()

    @property
    def is_bullish_pressure(self) -> bool:
        return self.ewma_fast > 0.1

    @property
    def is_bearish_pressure(self) -> bool:
        return self.ewma_fast < -0.1


@dataclass
class CrossContractBBOSignal:
    """Aggregated BBO across ATM ± window."""
    net_imbalance: float = 0.0
    persistence: float = 0.0
    num_contracts: int = 0
    atm_strike: float = 0.0


@dataclass
class _SymbolState:
    ewma_fast: float = 0.0
    ewma_slow: float = 0.0
    last_update: float = 0.0


class BBOv2:
    """Multi-layer L2 BBO imbalance calculator.

    Usage (per symbol)::

        bbo = BBOv2()
        bbo.update(symbol="SPY250303C00560000", bids=bids_l2, asks=asks_l2)
        sig = bbo.get_signal("SPY250303C00560000")

    Usage (cross-contract)::

        cross = bbo.get_cross_contract_signal(
            symbols=["SPY...560C", "SPY...557C", ...],
            atm_strike=560.0,
        )

    rust_kernel Bridge (Phase 2):
        When _RUST_AVAILABLE, update() inner loop will be handled by
        rust_kernel.compute_bbo_weighted() for branchless SIMD execution.
    """

    def __init__(
        self,
        alpha_fast: float = _EWMA_ALPHA_FAST,
        alpha_slow: float = _EWMA_ALPHA_SLOW,
        max_levels: int = 5,
    ) -> None:
        self._alpha_fast = alpha_fast
        self._alpha_slow = alpha_slow
        self._max_levels = max_levels
        self._state: dict[str, _SymbolState] = {}
        self._last_raw: dict[str, float] = {}

    def update(
        self,
        symbol: str,
        bids: list[Any],
        asks: list[Any],
    ) -> BBOSignal:
        """Update BBO imbalance from a depth event.

        Args:
            symbol: Option symbol.
            bids:   List of bid objects with .volume and .price attributes
                    (or dicts with 'volume'/'price' keys). Top of book first.
            asks:   Same format for asks.

        Returns:
            Updated BBOSignal for this symbol.
        """
        if symbol not in self._state:
            self._state[symbol] = _SymbolState()

        raw = self._compute_weighted_imbalance(bids, asks)
        self._last_raw[symbol] = raw

        st = self._state[symbol]
        now = time.monotonic()

        # EWMA updates
        st.ewma_fast += self._alpha_fast * (raw - st.ewma_fast)
        st.ewma_slow += self._alpha_slow * (raw - st.ewma_slow)
        st.last_update = now

        n = min(len(bids), len(asks), self._max_levels)

        return BBOSignal(
            symbol=symbol,
            raw_imbalance=raw,
            ewma_fast=st.ewma_fast,
            ewma_slow=st.ewma_slow,
            persistence=abs(st.ewma_slow),
            depth_levels_used=n,
            timestamp=now,
        )

    def get_signal(self, symbol: str) -> Optional[BBOSignal]:
        """Return latest BBO signal for symbol (None if never updated)."""
        if symbol not in self._state:
            return None
        st = self._state[symbol]
        raw = self._last_raw.get(symbol, 0.0)
        return BBOSignal(
            symbol=symbol,
            raw_imbalance=raw,
            ewma_fast=st.ewma_fast,
            ewma_slow=st.ewma_slow,
            persistence=abs(st.ewma_slow),
            depth_levels_used=0,
            timestamp=st.last_update,
        )

    def get_all_snapshot(self) -> dict[str, BBOSignal]:
        """Snapshot of all tracked symbols."""
        return {sym: self.get_signal(sym) for sym in self._state if self.get_signal(sym)}

    def get_cross_contract_signal(
        self,
        symbols: list[str],
        atm_strike: float,
        window: float = 3.0,          # ± 3 points
    ) -> CrossContractBBOSignal:
        """Aggregate BBO across ATM ± window strikes.

        Only symbols whose state has been populated are included.
        """
        imbalances = []
        persistences = []

        for sym in symbols:
            sig = self.get_signal(sym)
            if sig is None:
                continue
            imbalances.append(sig.ewma_fast)
            persistences.append(sig.persistence)

        if not imbalances:
            return CrossContractBBOSignal(atm_strike=atm_strike)

        n = len(imbalances)
        return CrossContractBBOSignal(
            net_imbalance=sum(imbalances) / n,
            persistence=sum(persistences) / n,
            num_contracts=n,
            atm_strike=atm_strike,
        )

    # ── Private ──────────────────────────────────────────────────────────────

    def _compute_weighted_imbalance(
        self,
        bids: list[Any],
        asks: list[Any],
    ) -> float:
        """Compute price-level-weighted bid/ask imbalance.

        Formula:
            imbalance = Σ(w_i × bid_vol_i) - Σ(w_i × ask_vol_i)
                        ─────────────────────────────────────────
                        Σ(w_i × bid_vol_i) + Σ(w_i × ask_vol_i)

        Level weights: [1.0, 0.5, 0.333, 0.25, 0.20] (top 5 levels).
        """
        n = min(len(bids), len(asks), self._max_levels, len(_LEVEL_WEIGHTS))
        if n == 0:
            return 0.0

        if _RUST_AVAILABLE:
            bids_v = [self._get_vol(bids[i]) for i in range(n)]
            asks_v = [self._get_vol(asks[i]) for i in range(n)]
            return _rust.compute_bbo_weighted(bids_v, asks_v, self._max_levels)

        w_bid = w_ask = 0.0
        for i in range(n):
            w = _LEVEL_WEIGHTS[i]
            bid_vol = self._get_vol(bids[i])
            ask_vol = self._get_vol(asks[i])
            w_bid += w * bid_vol
            w_ask += w * ask_vol

        total = w_bid + w_ask
        if total <= 0:
            return 0.0
        return (w_bid - w_ask) / total

    @staticmethod
    def _get_vol(level: Any) -> float:
        """Extract volume from either an object attribute or dict key."""
        if hasattr(level, "volume"):
            return max(0.0, float(getattr(level, "volume", 0)))
        if isinstance(level, dict):
            return max(0.0, float(level.get("volume", 0)))
        return 0.0

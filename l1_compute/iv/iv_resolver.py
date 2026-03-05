"""IV Resolver — Priority cascade for implied volatility resolution.

Resolution priority (waterfall):
    1. WS (WebSocket) IV  — freshest; accepted if age < TTL (2 hours)
    2. REST baseline IV   — from IVBaselineSync polling cache
    3. Chain entry IV     — raw from Longport option_detail
    4. SABR interpolation — if SABRCalibrator has valid params
    5. None               — symbol excluded from Greeks computation

After selecting the raw IV, applies Sticky-Strike momentum adjustment
using the spot price differential since the last IV sync.

Outputs a `ResolvedIV` object which records the source for observability.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# WS IV time-to-live: if iv_timestamp is older than this, discard WS IV.
_WS_IV_TTL: float = 7200.0   # seconds (2 hours)
_IV_CLAMP_LOW:  float = 0.01
_IV_CLAMP_HIGH: float = 5.0
_SKEW_SENSITIVITY: float = 2.0   # calibrated for SPY 0DTE daily dynamics


class IVSource(str, Enum):
    WS      = "ws"
    REST    = "rest"
    CHAIN   = "chain"
    SABR    = "sabr"
    MISSING = "missing"


@dataclass
class ResolvedIV:
    """Resolved implied volatility with metadata."""
    value: float              # Adjusted IV decimal (e.g. 0.20)
    source: IVSource
    raw_value: float          # Pre-adjustment value (for diagnostics)
    confidence: float         # 1.0 = WS fresh, 0.8 = REST, 0.5 = chain, 0.3 = SABR

    @property
    def is_valid(self) -> bool:
        return self.value > 0 and self.source != IVSource.MISSING


@dataclass
class IVResolutionStats:
    """Counters for observability."""
    ws_hits: int = 0
    rest_hits: int = 0
    chain_hits: int = 0
    sabr_hits: int = 0
    misses: int = 0


class IVResolver:
    """Resolves implied volatility for each option contract.

    Usage::

        resolver = IVResolver()
        iv = resolver.resolve(
            symbol="SPY250303C00560000",
            ws_iv=0.21, ws_iv_timestamp=<monotonic>,
            rest_iv=0.20, chain_iv=0.19,
            spot=560.5, spot_ref=560.0,
            opt_type="CALL",
        )
        if iv.is_valid:
            use(iv.value)
    """

    def __init__(
        self,
        ws_ttl: float = _WS_IV_TTL,
        skew_sensitivity: float = _SKEW_SENSITIVITY,
        sabr_calibrator: Optional["SABRCalibrator"] = None,  # noqa: F821
    ) -> None:
        self._ws_ttl = ws_ttl
        self._skew_sensitivity = skew_sensitivity
        self._sabr = sabr_calibrator
        self.stats = IVResolutionStats()

    def resolve(
        self,
        symbol: str,
        ws_iv: Optional[float],
        ws_iv_timestamp: Optional[float],   # monotonic seconds (from time.monotonic())
        rest_iv: Optional[float],
        chain_iv: Optional[float],
        spot: float,
        spot_ref: float,                    # spot at last REST sync
        opt_type: str,                      # "CALL" | "PUT"
        strike: Optional[float] = None,     # needed for SABR
        ttm_years: Optional[float] = None,  # needed for SABR
    ) -> ResolvedIV:
        """Resolve IV for a single contract using the priority waterfall.

        Returns ResolvedIV with adjusted IV and source metadata.
        """
        now_mono = time.monotonic()
        raw_iv, source, confidence = self._select_raw_iv(
            ws_iv, ws_iv_timestamp, now_mono, rest_iv, chain_iv,
            symbol, strike, ttm_years,
        )

        if raw_iv is None:
            self.stats.misses += 1
            return ResolvedIV(value=0.0, source=IVSource.MISSING, raw_value=0.0, confidence=0.0)

        # Apply Sticky-Strike momentum adjustment
        adjusted = self._skew_adjust(raw_iv, spot, spot_ref, opt_type)

        return ResolvedIV(value=adjusted, source=source, raw_value=raw_iv, confidence=confidence)

    def batch_resolve(
        self,
        entries: Union[list[dict], Any],
        spot: float,
        iv_cache: dict[str, float],
        spot_at_sync: dict[str, float],
        ttm_years: Optional[float] = None,
    ) -> dict[str, ResolvedIV]:
        """Resolve IV for all chain entries in one pass.

        Args:
            entries:     List of chain entry dicts (from ChainStateStore / L0) or pa.RecordBatch.
            spot:        Current spot price.
            iv_cache:    REST IV cache {symbol: iv}.
            spot_at_sync: {symbol: spot_at_rest_sync_time}.

        Returns:
            Dict of {symbol: ResolvedIV}.
        """
        now_mono = time.monotonic()
        result: dict[str, ResolvedIV] = {}
        
        import pyarrow as pa
        if isinstance(entries, pa.RecordBatch):
            entries = entries.to_pylist()

        for entry in entries:
            symbol: str = entry.get("symbol", "")
            
            # Support both legacy "type" string and Arrow "is_call" boolean
            is_call_raw = entry.get("is_call")
            if is_call_raw is not None:
                opt_type = "CALL" if is_call_raw else "PUT"
            else:
                opt_type = str(entry.get("type", "CALL")).upper()
                
            strike   = float(entry.get("strike", 0.0))
            
            # Support both legacy "implied_volatility" and Arrow "iv"
            ws_iv    = entry.get("implied_volatility")
            if ws_iv is None:
                ws_iv = entry.get("iv")
                
            ws_ts    = entry.get("iv_timestamp", 0.0)
            rest_iv  = iv_cache.get(symbol)
            chain_iv = ws_iv or 0.0
            spot_ref = spot_at_sync.get(symbol, spot)

            # Avoid re-using same ws_iv as both ws and chain when iv_timestamp is missing
            if ws_ts == 0.0:
                chain_only_iv = chain_iv
                ws_only_iv = None
            else:
                chain_only_iv = None
                ws_only_iv = ws_iv

            result[symbol] = self.resolve(
                symbol=symbol,
                ws_iv=ws_only_iv,
                ws_iv_timestamp=ws_ts,
                rest_iv=rest_iv,
                chain_iv=chain_only_iv,
                spot=spot,
                spot_ref=spot_ref,
                opt_type=opt_type,
                strike=strike,
                ttm_years=ttm_years,
            )

        return result

    # ── Private ─────────────────────────────────────────────────────────────────

    def _select_raw_iv(
        self,
        ws_iv: Optional[float],
        ws_ts: Optional[float],
        now_mono: float,
        rest_iv: Optional[float],
        chain_iv: Optional[float],
        symbol: str,
        strike: Optional[float],
        ttm_years: Optional[float],
    ) -> tuple[Optional[float], IVSource, float]:
        # Tier 1: WS IV (freshness checked)
        if ws_iv and ws_iv > 0 and ws_ts is not None:
            age = now_mono - ws_ts
            if age < self._ws_ttl:
                self.stats.ws_hits += 1
                return ws_iv, IVSource.WS, 1.0

        # Tier 2: REST baseline
        if rest_iv and rest_iv > 0:
            self.stats.rest_hits += 1
            return rest_iv, IVSource.REST, 0.8

        # Tier 3: Chain entry IV
        if chain_iv and chain_iv > 0:
            self.stats.chain_hits += 1
            return chain_iv, IVSource.CHAIN, 0.5

        # Tier 4: SABR interpolation
        if self._sabr and self._sabr.is_calibrated and strike and ttm_years:
            try:
                sabr_iv = self._sabr.interpolate(strike, ttm_years)
                if sabr_iv > 0:
                    self.stats.sabr_hits += 1
                    return sabr_iv, IVSource.SABR, 0.3
            except Exception as exc:
                logger.debug("[IVResolver] SABR interpolation failed for %s: %s", symbol, exc)

        return None, IVSource.MISSING, 0.0

    def _skew_adjust(
        self,
        cached_iv: float,
        spot_now: float,
        spot_ref: float,
        opt_type: str,
    ) -> float:
        """Sticky-Strike IV momentum correction (from bsm.py:skew_adjust_iv)."""
        if spot_ref <= 0 or spot_now <= 0:
            return max(_IV_CLAMP_LOW, min(_IV_CLAMP_HIGH, cached_iv))

        log_ret = math.log(spot_now / spot_ref)
        is_call = opt_type.upper() in ("CALL", "C")
        delta_iv = self._skew_sensitivity * log_ret if is_call else -self._skew_sensitivity * log_ret

        return max(_IV_CLAMP_LOW, min(_IV_CLAMP_HIGH, cached_iv + delta_iv))

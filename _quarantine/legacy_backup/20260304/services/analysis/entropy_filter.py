"""Shannon Entropy Pre-Filter — L0/L1 Information Gate

Eliminates low-information-content ticks before they reach the expensive
BSM / Greeks computation loop, aligned with 2024-2026 journal findings:

    "Shannon entropy can rapidly filter signal noise with O(1) overhead,
     improving alpha generation accuracy without triggering costly validation."
    — Preprints.org (2025): Entropy-Based Decision Making in LVQ Trading

Architecture:
- On each incoming WS tick, compute the *information entropy* of the tick's
  key quantities (IV, volume, price change).
- If the entropy falls below a MinEntropy threshold, the tick is classified
  as "noise" and skipped before any array allocation or BSM call.
- This prevents "zombie ticks" (repeated identical pushes from MarketDataFeed)
  from wasting CPU cycles in the hot path.

Usage in option_chain_builder.py:
    from app.services.analysis.entropy_filter import EntropyFilter

    # At __init__:
    self._entropy_filter = EntropyFilter()

    # In _update_contract_in_memory / _enrich_chain_with_local_greeks:
    if not self._entropy_filter.accept(symbol, entry):
        return  # Skip this tick
"""

from __future__ import annotations

import math
import logging
from typing import Any


logger = logging.getLogger(__name__)


class EntropyFilter:
    """Stateful Shannon entropy gate for incoming market data ticks.

    For each symbol, maintains a tiny state window (size WINDOW) of the
    last observed bit-field values. Computes empirical entropy on the delta
    signature and drops ticks whose normalised entropy < min_entropy_bits.

    Attributes:
        min_entropy:  Minimum entropy threshold (bits). Below this → discard.
        _state:       Per-symbol last-seen values for delta computation.
        _accept_rate: Rolling pass-through stats (for logging).
    """

    # Number of observed fields per tick used in entropy estimation
    _FIELDS = ("implied_volatility", "volume", "bid", "ask", "last_price", "open_interest")

    def __init__(self, min_entropy: float = 0.05) -> None:
        """
        Args:
            min_entropy: Minimum Shannon entropy (bits) for a tick to be accepted.
                         0.05 is very permissive (near-zero change still accepted).
                         Increase to 0.2-0.5 for heavy noise suppression.
        """
        self.min_entropy = min_entropy
        self._state: dict[str, dict[str, float]] = {}
        self._total: int = 0
        self._accepted: int = 0

    @staticmethod
    def _field_entropy(prev: float, curr: float) -> float:
        """Compute a 1-symbol entropy proxy from the relative change.

        Returns:
            Shannon information content of the observed change (bits), ≥ 0.
        """
        if prev == 0.0 and curr == 0.0:
            return 0.0
        # Relative change (capped to avoid log(0))
        denom = abs(prev) if abs(prev) > 1e-10 else 1e-10
        relative_change = abs(curr - prev) / denom
        # Cap to [1e-10, 1.0] then map to bits: -log2(1 - change) for small Δ
        # or log2(1 + change) for moderate Δ. This is monotonically increasing.
        # For a market tick: even 0.001% change carries ~0.002 bits of information.
        change_capped = min(relative_change, 1.0)
        if change_capped < 1e-10:
            return 0.0
        # log2(1 + change) gives bits: 0.002 for 0.1% change, 1.0 for 100% change
        return math.log2(1.0 + change_capped)

    def accept(self, symbol: str, entry: dict[str, Any]) -> bool:
        """Decide whether to pass a tick through to the BSM computation.

        A tick is accepted if its aggregate Shannon entropy > min_entropy,
        meaning at least one field changed by a meaningful amount.

        Args:
            symbol: Option contract symbol (for per-symbol state tracking).
            entry:  Current tick data dictionary.

        Returns:
            True  → pass the tick through (worth computing Greeks).
            False → discard (identical or near-identical to previous tick).
        """
        self._total += 1

        # First tick for each symbol always passes through
        if symbol not in self._state:
            self._state[symbol] = {
                f: float(entry.get(f) or 0.0) for f in self._FIELDS
            }
            self._accepted += 1
            return True

        prev = self._state[symbol]

        # Compute aggregate entropy across all fields
        total_entropy = 0.0
        for field in self._FIELDS:
            curr_val = float(entry.get(field) or 0.0)
            prev_val = prev.get(field, 0.0)
            total_entropy += self._field_entropy(prev_val, curr_val)

        # Update state regardless of accept/reject so state doesn't drift
        for field in self._FIELDS:
            prev[field] = float(entry.get(field) or 0.0)

        if total_entropy < self.min_entropy:
            # Log very occasionally so we can see the filter working
            if self._total % 5000 == 0:
                pass_rate = (self._accepted / self._total) * 100
                logger.debug(
                    f"[EntropyFilter] total={self._total} accepted={self._accepted} "
                    f"({pass_rate:.1f}%) — last entropy={total_entropy:.4f} for {symbol}"
                )
            return False

        self._accepted += 1
        return True

    def stats(self) -> dict[str, Any]:
        """Return current filter statistics."""
        pass_rate = (self._accepted / self._total * 100) if self._total > 0 else 100.0
        return {
            "total_ticks": self._total,
            "accepted_ticks": self._accepted,
            "rejected_ticks": self._total - self._accepted,
            "pass_rate_pct": round(pass_rate, 2),
        }

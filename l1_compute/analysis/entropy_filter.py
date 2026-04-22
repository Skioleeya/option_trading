"""Shannon Entropy Pre-Filter - L0/L1 Information Gate."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from shared_rust.services import compute_entropy_gate as _rust_compute_entropy_gate  # type: ignore
    _RUST_AVAILABLE = True
except (ImportError, AttributeError):
    _rust_compute_entropy_gate = None
    _RUST_AVAILABLE = False


class EntropyFilter:
    _FIELDS = ("implied_volatility", "volume", "bid", "ask", "last_price", "open_interest")

    def _to_dict(self, entry: Any) -> dict:
        if isinstance(entry, dict):
            return entry
        if hasattr(entry, "model_dump"):
            return entry.model_dump()
        if hasattr(entry, "__dict__"):
            return entry.__dict__
        return {}

    def __init__(self, min_entropy: float = 0.05) -> None:
        self.min_entropy = min_entropy
        self._state: dict[str, dict[str, float]] = {}
        self._total: int = 0
        self._accepted: int = 0

    def accept(self, symbol: str, entry: Any) -> bool:
        self._total += 1
        data = self._to_dict(entry)

        if symbol not in self._state:
            self._state[symbol] = {f: float(data.get(f) or 0.0) for f in self._FIELDS}
            self._accepted += 1
            return True

        prev = self._state[symbol]
        features: list[float] = []
        for field in self._FIELDS:
            curr_val = float(data.get(field) or 0.0)
            prev_val = prev.get(field, 0.0)
            denom = abs(prev_val) if abs(prev_val) > 1e-10 else 1e-10
            features.append(abs(curr_val - prev_val) / denom)
            prev[field] = curr_val

        if not _RUST_AVAILABLE or _rust_compute_entropy_gate is None:
            raise RuntimeError("shared_rust.services.compute_entropy_gate unavailable")

        try:
            passed = bool(
                _rust_compute_entropy_gate(
                    features,
                    float(self.min_entropy),
                )
            )
        except Exception as exc:  # nosec B904 - explicit bridge failure context
            logger.error("[EntropyFilter] Rust entropy gate failed: %s", exc)
            raise RuntimeError("Rust entropy gate failed") from exc

        if not passed:
            if self._total % 5000 == 0:
                pass_rate = (self._accepted / self._total) * 100
                logger.debug(
                    f"[EntropyFilter] total={self._total} accepted={self._accepted} "
                    f"({pass_rate:.1f}%) - last gated tick={symbol}"
                )
            return False

        self._accepted += 1
        return True

    def stats(self) -> dict[str, Any]:
        pass_rate = (self._accepted / self._total * 100) if self._total > 0 else 100.0
        return {
            "total_ticks": self._total,
            "accepted_ticks": self._accepted,
            "rejected_ticks": self._total - self._accepted,
            "pass_rate_pct": round(pass_rate, 2),
        }

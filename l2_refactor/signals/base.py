"""l2_refactor.signals.base — SignalGenerator Protocol and base class.

Defines the structural contract that all signal generators must implement.
Uses typing.Protocol (structural subtyping) for maximum flexibility — generators
don't need to inherit from a base class, only satisfy the interface.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from l2_refactor.events.decision_events import FeatureVector, RawSignal

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Protocol (structural typing contract)
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class SignalGenerator(Protocol):
    """Structural interface for L2 signal generators.

    Any class implementing name + generate() + reset() satisfies this Protocol,
    regardless of inheritance hierarchy. Use isinstance(obj, SignalGenerator) to verify.
    """

    name: str

    def generate(self, features: FeatureVector) -> RawSignal:
        """Generate a signal from the current feature vector.

        Args:
            features: FeatureVector produced by FeatureStore.compute_all().

        Returns:
            RawSignal with direction, confidence, and raw_value fields populated.
            Must NEVER raise — return NEUTRAL on errors.
        """
        ...

    def reset(self) -> None:
        """Reset all internal state (call at session boundary / day change)."""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Base class (optional convenience — not required by Protocol)
# ─────────────────────────────────────────────────────────────────────────────

class SignalGeneratorBase:
    """Optional base class providing common utilities for signal generators.

    Subclass this for convenience, or implement SignalGenerator Protocol directly.
    """

    name: str = "base"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._tick_count: int = 0

    # ── Protocol methods ──────────────────────────────────────────────────────

    @abstractmethod
    def generate(self, features: FeatureVector) -> RawSignal:
        raise NotImplementedError

    def reset(self) -> None:
        """Reset state. Override to add stateful cleanup."""
        self._tick_count = 0

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _param(self, key: str, default: Any = None) -> Any:
        """Retrieve config parameter with fallback."""
        return self._config.get("parameters", {}).get(key, default)

    def _make_neutral(self, metadata: dict[str, float] | None = None) -> RawSignal:
        """Convenience: return a NEUTRAL signal."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        return RawSignal(
            name=self.name,
            direction="NEUTRAL",
            confidence=0.0,
            raw_value=0.0,
            computed_at=datetime.now(ZoneInfo("US/Eastern")),
            metadata=metadata or {},
        )

    def _make_signal(
        self,
        direction: str,
        confidence: float,
        raw_value: float,
        metadata: dict[str, float] | None = None,
    ) -> RawSignal:
        """Convenience: return a signal with validation."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        import math

        # Clamp and validate
        confidence = max(0.0, min(1.0, float(confidence)))
        raw_value = max(-1.0, min(1.0, float(raw_value)))
        if not math.isfinite(confidence):
            confidence = 0.0
        if not math.isfinite(raw_value):
            raw_value = 0.0
        if direction not in ("BULLISH", "BEARISH", "NEUTRAL"):
            direction = "NEUTRAL"

        return RawSignal(
            name=self.name,
            direction=direction,
            confidence=confidence,
            raw_value=raw_value,
            computed_at=datetime.now(ZoneInfo("US/Eastern")),
            metadata=metadata or {},
        )

    @staticmethod
    def _classify(value: float, bull_threshold: float, bear_threshold: float) -> str:
        """Map continuous value to directional string."""
        if value > bull_threshold:
            return "BULLISH"
        if value < bear_threshold:
            return "BEARISH"
        return "NEUTRAL"

    @staticmethod
    def _scale_confidence(
        value: float,
        reference: float,
        floor: float = 0.3,
    ) -> float:
        """Scale absolute value to confidence [floor, 1.0]."""
        if reference <= 0:
            return floor
        ratio = abs(value) / reference
        return min(1.0, floor + (1.0 - floor) * min(ratio, 1.0))

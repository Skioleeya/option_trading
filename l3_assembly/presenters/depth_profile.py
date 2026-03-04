"""l3_assembly.presenters.depth_profile — DepthProfilePresenterV2.

Wraps the legacy DepthProfilePresenter (EMA smoother, sticky cache, 3-tier GPU).
Returns tuple[DepthProfileRow, ...] instead of list[dict].
"""

from __future__ import annotations

from typing import Any

from l3_assembly.events.payload_events import DepthProfileRow


class DepthProfilePresenterV2:
    """Strongly-typed DepthProfile presenter."""

    @classmethod
    def build(
        cls,
        per_strike_gex: list[dict[str, Any]],
        spot: float | None,
        flip_level: float | None,
    ) -> tuple[DepthProfileRow, ...]:
        """Return typed tuple of DepthProfileRow.

        Delegates EMA computation and sticky-cache to the legacy presenter.
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[DepthProfilePresenterV2] build called with {len(per_strike_gex) if per_strike_gex else 0} strikes, spot={spot}")

        try:
            from l3_assembly.presenters.ui.depth_profile.presenter import DepthProfilePresenter
            raw_rows: list[dict[str, Any]] = DepthProfilePresenter.build(
                per_strike_gex=per_strike_gex,
                spot=spot,
                flip_level=flip_level,
            )
            logger.warning(f"[DepthProfilePresenterV2] inner build returned {len(raw_rows)} rows")
        except Exception as e:
            logger.error(f"[DepthProfilePresenterV2] inner build FAILED: {repr(e)}")
            raw_rows = []

        rows = []
        for r in raw_rows:
            try:
                rows.append(cls._row_from_dict(r))
            except (ValueError, TypeError):
                continue   # skip malformed rows from legacy presenter

        return tuple(rows)

    @staticmethod
    def _row_from_dict(d: dict[str, Any]) -> DepthProfileRow:
        import math
        call_pct = float(d.get("call_pct", 0.0) or 0.0)
        put_pct = float(d.get("put_pct", 0.0) or 0.0)
        # Guard against NaN/Inf from EMA on first tick
        if not math.isfinite(call_pct):
            call_pct = 0.0
        if not math.isfinite(put_pct):
            put_pct = 0.0
        return DepthProfileRow(
            strike=float(d.get("strike", 0.0) or 0.0),
            call_pct=call_pct,
            put_pct=put_pct,
            is_atm=bool(d.get("is_spot", False)), # Map legacy `is_spot` to `is_atm`
            is_flip=bool(d.get("is_flip", False)),
            is_dominant_put=bool(d.get("is_dominant_put", False)),
            is_dominant_call=bool(d.get("is_dominant_call", False)),
        )

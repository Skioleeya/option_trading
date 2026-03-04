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
        try:
            from app.ui.depth_profile.presenter import DepthProfilePresenter
            raw_rows: list[dict[str, Any]] = DepthProfilePresenter.build(
                per_strike_gex=per_strike_gex,
                spot=spot,
                flip_level=flip_level,
            )
        except ImportError:
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
        call_gex = float(d.get("call_gex", 0.0) or 0.0)
        put_gex = float(d.get("put_gex", 0.0) or 0.0)
        # Guard against NaN/Inf from EMA on first tick
        if not math.isfinite(call_gex):
            call_gex = 0.0
        if not math.isfinite(put_gex):
            put_gex = 0.0
        return DepthProfileRow(
            strike=float(d.get("strike", 0.0) or 0.0),
            call_gex=call_gex,
            put_gex=put_gex,
            is_atm=bool(d.get("is_atm", False)),
            is_flip=bool(d.get("is_flip", False)),
            pct_max=float(d.get("pct_max", 0.0) or 0.0),
        )

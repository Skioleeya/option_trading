"""l3_assembly.presenters.active_options — ActiveOptionsPresenterV2.

Wraps the legacy ActiveOptionsPresenter (DEG-FLOW composite engine + sticky cache).
Returns tuple[ActiveOptionRow, ...] instead of list[dict].

Note: The ActiveOptionsPresenter is stateful (owns FlowEngine instances and
      maintains the background cache). This V2 wrapper is a thin adapter
      that reads from the legacy cache via get_latest().
"""

from __future__ import annotations

from typing import Any

from l3_assembly.events.payload_events import ActiveOptionRow


class ActiveOptionsPresenterV2:
    """Strongly-typed ActiveOptions presenter adapter.

    Wraps an existing ActiveOptionsPresenter instance, not a class-method
    interface, because the legacy presenter maintains per-instance state
    (engine D/E/G, OI store, latest cache).
    """

    def __init__(self, legacy_presenter: Any) -> None:
        self._legacy = legacy_presenter

    def get_latest(self) -> tuple[ActiveOptionRow, ...]:
        """Return typed rows from the background-computed cache."""
        raw_rows: list[dict[str, Any]] = self._legacy.get_latest() or []
        rows = []
        for r in raw_rows:
            try:
                rows.append(self._row_from_dict(r))
            except (KeyError, TypeError, ValueError):
                continue
        return tuple(rows)

    @staticmethod
    def _row_from_dict(d: dict[str, Any]) -> ActiveOptionRow:
        option_type_raw = str(d.get("option_type", "CALL")).upper()
        option_type = "CALL" if option_type_raw in ("CALL", "C") else "PUT"
        return ActiveOptionRow(
            symbol=str(d.get("symbol", "SPY")),
            option_type=option_type,
            strike=float(d.get("strike", 0.0) or 0.0),
            implied_volatility=float(d.get("implied_volatility", 0.0) or 0.0),
            volume=int(d.get("volume", 0) or 0),
            turnover=float(d.get("turnover", 0.0) or 0.0),
            flow=float(d.get("flow", 0.0) or 0.0),
            impact_index=float(d.get("impact_index", 0.0) or 0.0),
            is_sweep=bool(d.get("is_sweep", False)),
            flow_deg_formatted=str(d.get("flow_deg_formatted", "$0")),
            flow_volume_label=str(d.get("flow_volume_label", "0")),
            flow_color=str(d.get("flow_color", "text-text-secondary")),
            flow_glow=str(d.get("flow_glow", "")),
            flow_intensity=str(d.get("flow_intensity", "LOW")),
            flow_direction=str(d.get("flow_direction", "NEUTRAL")),
            flow_d_z=float(d.get("flow_d_z", 0.0) or 0.0),
            flow_e_z=float(d.get("flow_e_z", 0.0) or 0.0),
            flow_g_z=float(d.get("flow_g_z", 0.0) or 0.0),
        )

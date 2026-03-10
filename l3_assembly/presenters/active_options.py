"""l3_assembly.presenters.active_options — ActiveOptionsPresenterV2.

Wraps the legacy ActiveOptionsPresenter (DEG-FLOW composite engine + sticky cache).
Returns tuple[ActiveOptionRow, ...] instead of list[dict].

Note: The ActiveOptionsPresenter is stateful (owns FlowEngine instances and
      maintains the background cache). This V2 wrapper is a thin adapter
      that reads from the legacy cache via get_latest().
"""

from __future__ import annotations

from typing import Any

from l3_assembly.events.active_options_contract import active_option_row_from_dict
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
                rows.append(active_option_row_from_dict(r))
            except (KeyError, TypeError, ValueError):
                continue
        return tuple(rows)

    @staticmethod
    def _row_from_dict(d: dict[str, Any]) -> ActiveOptionRow:
        return active_option_row_from_dict(d)

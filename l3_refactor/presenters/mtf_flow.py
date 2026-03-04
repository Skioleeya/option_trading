"""l3_refactor.presenters.mtf_flow — MTFFlowPresenterV2."""

from __future__ import annotations

from typing import Any

from l3_refactor.events.payload_events import MTFFlowState


class MTFFlowPresenterV2:
    """Strongly-typed MTF Flow presenter."""

    @classmethod
    def build(cls, mtf_consensus: dict[str, Any]) -> MTFFlowState:
        try:
            from app.ui.mtf_flow.presenter import MTFFlowPresenter
            raw = MTFFlowPresenter.build(mtf_consensus=mtf_consensus)
        except ImportError:
            raw = {}

        return MTFFlowState(
            m1=dict(raw.get("m1", {})),
            m5=dict(raw.get("m5", {})),
            m15=dict(raw.get("m15", {})),
            consensus=str(raw.get("consensus", "NEUTRAL")),
            strength=float(raw.get("strength", 0.0) or 0.0),
            alignment=float(raw.get("alignment", 0.0) or 0.0),
            align_label=str(raw.get("align_label", "SPLIT")),
            align_color=str(raw.get("align_color", "text-text-secondary")),
        )

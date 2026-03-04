"""l3_assembly.presenters.tactical_triad — TacticalTriadPresenterV2."""

from __future__ import annotations

from typing import Any

from l3_assembly.events.payload_events import TacticalTriadState


class TacticalTriadPresenterV2:
    """Strongly-typed TacticalTriad presenter."""

    @classmethod
    def build(
        cls,
        vrp: float | None,
        vrp_state: str | None,
        net_charm: float | None,
        svol_corr: float | None,
        svol_state: str | None,
        fused_signal_direction: str | None = None,
    ) -> TacticalTriadState:
        try:
            from app.ui.tactical_triad.presenter import TacticalTriadPresenter
            raw = TacticalTriadPresenter.build(
                vrp=vrp, vrp_state=vrp_state, net_charm=net_charm,
                svol_corr=svol_corr, svol_state=svol_state,
                fused_signal_direction=fused_signal_direction,
            )
        except ImportError:
            raw = {"vrp": {}, "charm": {}, "svol": {}}

        return TacticalTriadState(
            vrp=dict(raw.get("vrp", {})),
            charm=dict(raw.get("charm", {})),
            svol=dict(raw.get("svol", {})),
        )

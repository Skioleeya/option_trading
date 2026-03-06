"""l3_assembly.presenters.micro_stats — MicroStatsPresenterV2.

Wraps the legacy MicroStatsPresenter logic (debounce + lookup tables)
and returns a typed MicroStatsState instead of dict[str, Any].

Numeric parity guarantee:
    MicroStatsPresenterV2.build(...).to_dict() == MicroStatsPresenter.build(...)
"""

from __future__ import annotations

from typing import Any

from l3_assembly.events.payload_events import (
    MetricCard,
    MicroStatsState,
    VALID_BADGE_TOKENS,
)


# ── Badge normalizer ── keeps frontend token semantics while supporting aliases
_BADGE_ALIASES: dict[str, str] = {
    "badge-super-pin": "badge-amber",
    "badge-damping": "badge-hollow-green",
    "badge-acceleration": "badge-hollow-purple",
    "positive": "badge-positive",
    "negative": "badge-negative",
    "neutral": "badge-neutral",
    "warning": "badge-warning",
    "danger": "badge-danger",
}


def _normalize_badge(raw: str) -> str:
    """Map legacy aliases to valid frontend badge tokens."""
    token = str(raw or "").strip()
    if token in VALID_BADGE_TOKENS:
        return token
    if token in _BADGE_ALIASES:
        return _BADGE_ALIASES[token]
    return _BADGE_ALIASES.get(token.lower(), "badge-neutral")


class MicroStatsPresenterV2:
    """Strongly-typed MicroStats presenter.

    Delegates computation entirely to the legacy presenter, then wraps
    the dict output into a typed MicroStatsState.

    Usage:
        state = MicroStatsPresenterV2.build(gex_regime, wall_dyn, vanna, momentum)
        d = state.to_dict()   # identical to legacy output
    """

    @classmethod
    def build(
        cls,
        gex_regime: str,
        wall_dyn: dict[str, Any],
        vanna: str,
        momentum: str,
    ) -> MicroStatsState:
        """Build typed MicroStatsState by calling the legacy presenter."""
        try:
            from l3_assembly.presenters.ui.micro_stats.presenter import MicroStatsPresenter
            raw = MicroStatsPresenter.build(
                gex_regime=gex_regime,
                wall_dyn=wall_dyn,
                vanna=vanna,
                momentum=momentum,
            )
        except ImportError:
            # Legacy backend not on path (e.g. isolated test env) — use minimal fallback
            raw = cls._fallback_build(gex_regime, wall_dyn, vanna, momentum)

        return cls._dict_to_state(raw)

    @classmethod
    def _dict_to_state(cls, raw: dict[str, Any]) -> MicroStatsState:
        """Convert legacy dict output to typed MicroStatsState."""

        def _card(d: Any) -> MetricCard:
            if isinstance(d, dict):
                return MetricCard(
                    label=str(d.get("label", "—")),
                    badge=_normalize_badge(str(d.get("badge", "badge-neutral"))),
                    tooltip=str(d.get("tooltip", "")),
                )
            return MetricCard(label="—", badge="badge-neutral")

        return MicroStatsState(
            net_gex=_card(raw.get("net_gex")),
            wall_dyn=_card(raw.get("wall_dyn")),
            vanna=_card(raw.get("vanna")),
            momentum=_card(raw.get("momentum")),
        )

    @staticmethod
    def _fallback_build(
        gex_regime: str,
        wall_dyn: dict[str, Any],
        vanna: str,
        momentum: str,
    ) -> dict[str, Any]:
        """Minimal fallback for when legacy presenter is unavailable."""
        neutral_card = {"label": "—", "badge": "badge-neutral"}
        return {
            "net_gex":  {"label": gex_regime or "NEUTRAL", "badge": "badge-neutral"},
            "wall_dyn": neutral_card,
            "vanna":    {"label": vanna or "NORMAL",   "badge": "badge-neutral"},
            "momentum": {"label": momentum or "NEUTRAL", "badge": "badge-neutral"},
        }

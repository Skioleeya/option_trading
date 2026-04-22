"""VRP and peak-impact feature spec builders."""

from __future__ import annotations

from typing import Any

from l2_decision.feature_store.extractors_common import _get_agg, _safe
from l2_decision.feature_store.store import FeatureSpec
from shared.config import settings
from shared_rust.services import tactical_compute_vrp as compute_vrp

_TTL_FAST_SECONDS = 1.0


def build_vrp_and_impact_specs(bundle: Any) -> list[FeatureSpec]:
    return [
        FeatureSpec(
            name="vol_risk_premium",
            extractor=lambda s: _safe(
                lambda: compute_vrp(_get_agg(s, "atm_iv", 0.0), settings.vrp_baseline_hv)
            ),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="ATM IV minus baseline HV in percent points (decimal/percent baseline auto-normalized)",
            tags=["iv", "regime", "vrp"],
        ),
        FeatureSpec(
            name="vrp_realized_based",
            extractor=bundle.vrp_realized_based,
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Research-path VRP in percent points using rolling realized volatility baseline",
            tags=["iv", "research", "vrp", "canonical"],
        ),
        FeatureSpec(
            name="peak_impact",
            extractor=bundle.max_impact,
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Peak institutional impact index proxy (max flow * gamma)",
            tags=["institutional", "threat"],
        ),
    ]

"""MM flow feature spec builders."""

from __future__ import annotations

from l2_decision.feature_store.extractors_common import _get_mm_metric
from l2_decision.feature_store.store import FeatureSpec

_TTL_FAST_SECONDS = 1.0


def build_mm_flow_specs() -> list[FeatureSpec]:
    return [
        FeatureSpec(
            name="net_delta_exposure_live",
            extractor=lambda s: _get_mm_metric(s, "net_delta_exposure_live", 0.0),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Live MM net delta exposure proxy from Rust snapshot aggregation",
            tags=["mm-flow", "delta", "exposure"],
        ),
        FeatureSpec(
            name="net_gamma_exposure_live",
            extractor=lambda s: _get_mm_metric(s, "net_gamma_exposure_live", 0.0),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Live MM net gamma exposure proxy from Rust snapshot aggregation",
            tags=["mm-flow", "gamma", "exposure"],
        ),
        FeatureSpec(
            name="residual_delta_after_netting",
            extractor=lambda s: _get_mm_metric(s, "residual_delta_after_netting", 0.0),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Residual delta after snapshot-level long/short netting",
            tags=["mm-flow", "delta", "spread"],
        ),
        FeatureSpec(
            name="oi_participation_ratio_live",
            extractor=lambda s: _get_mm_metric(s, "oi_participation_ratio_live", 0.0),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Average per-row size/OI participation proxy for live flow pressure",
            tags=["mm-flow", "oi", "participation"],
        ),
        FeatureSpec(
            name="flow_suppression_bias",
            extractor=lambda s: _get_mm_metric(s, "flow_suppression_bias", 0.0),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Suppression bias: (put ask + call bid) - (call ask + put bid)",
            tags=["mm-flow", "pressure", "suppression"],
        ),
        FeatureSpec(
            name="flow_dominance_ratio",
            extractor=lambda s: _get_mm_metric(s, "flow_dominance_ratio", 0.0),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Suppression dominance ratio normalized by total directional side volume",
            tags=["mm-flow", "pressure", "ratio"],
        ),
        FeatureSpec(
            name="midpoint_tickrule_count",
            extractor=lambda s: _get_mm_metric(s, "midpoint_tickrule_count", 0.0),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Count of midpoint prints requiring tick-rule direction inference",
            tags=["mm-flow", "microstructure", "tick-rule"],
        ),
        FeatureSpec(
            name="condition_filtered_count",
            extractor=lambda s: _get_mm_metric(s, "condition_filtered_count", 0.0),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Count of filtered condition-code trades (late/avg/out-of-seq)",
            tags=["mm-flow", "microstructure", "compliance"],
        ),
        FeatureSpec(
            name="complex_spread_count",
            extractor=lambda s: _get_mm_metric(s, "complex_spread_count", 0.0),
            ttl_seconds=_TTL_FAST_SECONDS,
            description="Detected complex spread cluster count in current snapshot",
            tags=["mm-flow", "spread", "netting"],
        ),
    ]


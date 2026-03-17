"""Feature extractor registry and default spec builder."""

from __future__ import annotations

from dataclasses import dataclass

from l2_decision.feature_store.extractors_common import (
    _get_agg,
    _get_agg_first,
    _get_ms,
    _get_val,
    _safe,
)
from l2_decision.feature_store.extractors_flow import (
    _IVVelocityExtractor,
    _MTFConsensusExtractor,
    _MaxImpactExtractor,
    _SVolCorrelationExtractor,
    _SpotRoCExtractor,
    _TurnoverVelocityExtractor,
    _WallMigrationSpeedExtractor,
)
from l2_decision.feature_store.extractors_skew import (
    _RR25CallMinusPutExtractor,
    _Skew25dExtractor,
    _Skew25dMetricsExtractor,
    _Skew25dValidExtractor,
)
from l2_decision.feature_store.extractors_volatility import (
    _RealizedVolatilityExtractor,
    _RealizedVolatilityMetricsExtractor,
    _RealizedVrpExtractor,
)
from l2_decision.feature_store.store import FeatureSpec
from shared.config import settings
from shared.system.tactical_triad_logic import compute_vrp

WINDOW_1M_SECONDS = 60.0
WINDOW_30S_SECONDS = 30.0
WINDOW_15M_SECONDS = 900.0
SKEW_DELTA_TOLERANCE = 0.10
REALIZED_VOL_MIN_SAMPLES = 5
TTL_FAST_SECONDS = 1.0
TTL_MEDIUM_SECONDS = 5.0
TTL_LONG_SECONDS = 15.0
NET_GEX_NORMALIZER = 1000.0


@dataclass
class _ExtractorBundle:
    spot_roc: _SpotRoCExtractor
    iv_vel: _IVVelocityExtractor
    wall_speed: _WallMigrationSpeedExtractor
    svol_corr: _SVolCorrelationExtractor
    mtf_consensus: _MTFConsensusExtractor
    skew_25d: _Skew25dExtractor
    skew_25d_valid: _Skew25dValidExtractor
    rr25_call_minus_put: _RR25CallMinusPutExtractor
    realized_vol: _RealizedVolatilityExtractor
    vrp_realized_based: _RealizedVrpExtractor
    turnover_vel: _TurnoverVelocityExtractor
    max_impact: _MaxImpactExtractor


def _build_bundle() -> _ExtractorBundle:
    skew_metrics = _Skew25dMetricsExtractor(delta_tolerance=SKEW_DELTA_TOLERANCE)
    realized_metrics = _RealizedVolatilityMetricsExtractor(
        window_seconds=WINDOW_15M_SECONDS,
        min_samples=REALIZED_VOL_MIN_SAMPLES,
    )
    return _ExtractorBundle(
        spot_roc=_SpotRoCExtractor(window_seconds=WINDOW_1M_SECONDS),
        iv_vel=_IVVelocityExtractor(window_seconds=WINDOW_1M_SECONDS),
        wall_speed=_WallMigrationSpeedExtractor(window_seconds=WINDOW_30S_SECONDS),
        svol_corr=_SVolCorrelationExtractor(window_seconds=WINDOW_15M_SECONDS),
        mtf_consensus=_MTFConsensusExtractor(),
        skew_25d=_Skew25dExtractor(skew_metrics),
        skew_25d_valid=_Skew25dValidExtractor(skew_metrics),
        rr25_call_minus_put=_RR25CallMinusPutExtractor(skew_metrics),
        realized_vol=_RealizedVolatilityExtractor(realized_metrics),
        vrp_realized_based=_RealizedVrpExtractor(realized_metrics),
        turnover_vel=_TurnoverVelocityExtractor(),
        max_impact=_MaxImpactExtractor(),
    )


def _build_core_specs(bundle: _ExtractorBundle) -> list[FeatureSpec]:
    specs: list[FeatureSpec] = []
    specs.extend(_build_core_market_specs(bundle))
    specs.extend(_build_core_structure_specs(bundle))
    return specs


def _build_core_market_specs(bundle: _ExtractorBundle) -> list[FeatureSpec]:
    return [
        FeatureSpec(
            name="spot_roc_1m",
            extractor=bundle.spot_roc,
            ttl_seconds=TTL_FAST_SECONDS,
            description="1-minute spot price rate-of-change (fractional)",
            tags=["momentum", "spot"],
        ),
        FeatureSpec(
            name="turnover_velocity",
            extractor=bundle.turnover_vel,
            ttl_seconds=TTL_FAST_SECONDS,
            description="Institutional turnover speed (USD/sec)",
            tags=["microstructure", "flow", "institutional"],
        ),
        FeatureSpec(
            name="atm_iv",
            extractor=lambda s: _get_agg(s, "atm_iv", 0.0),
            ttl_seconds=TTL_FAST_SECONDS,
            description="ATM implied volatility (annualized)",
            tags=["iv", "regime"],
        ),
        FeatureSpec(
            name="net_gex_normalized",
            extractor=lambda s: _safe(
                lambda: max(-1.0, min(1.0, _get_agg(s, "net_gex", 0.0) / NET_GEX_NORMALIZER))
            ),
            ttl_seconds=TTL_FAST_SECONDS,
            description="OI-based net GEX proxy (MMUSD) normalized by $1B reference (/1000)",
            tags=["gex", "regime"],
        ),
        FeatureSpec(
            name="vpin_composite",
            extractor=lambda s: _get_ms(s, "vpin_composite", 0.0),
            ttl_seconds=TTL_FAST_SECONDS,
            description="Composite VPIN toxicity score [0, 1]",
            tags=["microstructure", "flow"],
        ),
    ]


def _build_core_structure_specs(bundle: _ExtractorBundle) -> list[FeatureSpec]:
    return [
        FeatureSpec(
            name="bbo_imbalance_ewma",
            extractor=lambda s: _safe(lambda: max(-1.0, min(1.0, _get_ms(s, "bbo_ewma_fast", 0.0)))),
            ttl_seconds=TTL_FAST_SECONDS,
            description="BBO imbalance fast EWMA, clamped to [-1, 1]",
            tags=["microstructure", "orderbook"],
        ),
        FeatureSpec(
            name="call_wall_distance",
            extractor=lambda s: _safe(
                lambda: (_get_agg(s, "call_wall", 0.0) - _get_val(s, "spot", 0.0)) / _get_val(s, "spot", 1.0)
                if _get_val(s, "spot", 0.0) > 0
                else 0.0
            ),
            ttl_seconds=TTL_FAST_SECONDS,
            description="(call_wall proxy - spot) / spot — distance to trading-practice resistance proxy",
            tags=["gex", "structure"],
        ),
        FeatureSpec(
            name="iv_velocity_1m",
            extractor=bundle.iv_vel,
            ttl_seconds=TTL_FAST_SECONDS,
            description="1-min IV velocity, scaled to [-1, +1]",
            tags=["iv", "momentum"],
        ),
        FeatureSpec(
            name="wall_migration_speed",
            extractor=bundle.wall_speed,
            ttl_seconds=TTL_MEDIUM_SECONDS,
            description="Call+put wall migration speed, normalized [0, 1]",
            tags=["gex", "structure", "momentum"],
        ),
        FeatureSpec(
            name="svol_correlation_15m",
            extractor=bundle.svol_corr,
            ttl_seconds=TTL_LONG_SECONDS,
            description="15-min Pearson correlation (spot, IV). Negative=normal.",
            tags=["vanna", "regime"],
        ),
        FeatureSpec(
            name="vol_accel_ratio",
            extractor=lambda s: _safe(lambda: max(-1.0, min(1.0, (_get_ms(s, "vol_accel_ratio", 1.0) - 1.0)))),
            ttl_seconds=TTL_FAST_SECONDS,
            description="Vol accel ratio minus 1.0, clamped to [-1,+1]",
            tags=["microstructure", "momentum"],
        ),
    ]


def _build_skew_specs(bundle: _ExtractorBundle) -> list[FeatureSpec]:
    return [
        FeatureSpec(
            name="skew_25d_normalized",
            extractor=bundle.skew_25d,
            ttl_seconds=TTL_MEDIUM_SECONDS,
            description=(
                "Legacy normalized skew contract: (put_iv - call_iv) / atm_iv "
                "using nearest ±25d legs and IV priority computed_iv>iv>implied_volatility"
            ),
            tags=["skew", "regime"],
        ),
        FeatureSpec(
            name="rr25_call_minus_put",
            extractor=bundle.rr25_call_minus_put,
            ttl_seconds=TTL_MEDIUM_SECONDS,
            description=(
                "Canonical RR25 contract: call_iv(+0.25 delta) - put_iv(-0.25 delta) "
                "using IV priority computed_iv>iv>implied_volatility"
            ),
            tags=["skew", "regime", "canonical"],
        ),
        FeatureSpec(
            name="skew_25d_valid",
            extractor=bundle.skew_25d_valid,
            ttl_seconds=TTL_MEDIUM_SECONDS,
            description="1.0 when both ±25d legs are valid within delta tolerance; otherwise 0.0",
            tags=["skew", "quality"],
        ),
    ]


def _build_volatility_specs(bundle: _ExtractorBundle) -> list[FeatureSpec]:
    return [
        FeatureSpec(
            name="realized_volatility_15m",
            extractor=bundle.realized_vol,
            ttl_seconds=TTL_FAST_SECONDS,
            description="Rolling 15-minute annualized realized volatility (decimal) from spot log returns",
            tags=["iv", "research", "realized-vol"],
        ),
        FeatureSpec(
            name="mtf_consensus_score",
            extractor=bundle.mtf_consensus,
            ttl_seconds=TTL_MEDIUM_SECONDS,
            description="Multi-timeframe IV velocity consensus [-1, +1]",
            tags=["iv", "mtf", "regime"],
        ),
    ]


def _build_sensitivity_specs() -> list[FeatureSpec]:
    return [
        FeatureSpec(
            name="net_charm_raw_sum",
            extractor=lambda s: _get_agg_first(s, ("net_charm_raw_sum", "net_charm"), 0.0),
            ttl_seconds=TTL_FAST_SECONDS,
            description="Canonical raw chain sum of charm sensitivities; not position-weighted exposure",
            tags=["gex", "charm", "sensitivity", "canonical"],
        ),
        FeatureSpec(
            name="net_charm",
            extractor=lambda s: _get_agg_first(s, ("net_charm_raw_sum", "net_charm"), 0.0),
            ttl_seconds=TTL_FAST_SECONDS,
            description="Legacy alias of net_charm_raw_sum",
            tags=["gex", "charm", "sensitivity"],
        ),
        FeatureSpec(
            name="net_vanna_raw_sum",
            extractor=lambda s: _get_agg_first(s, ("net_vanna_raw_sum", "net_vanna"), 0.0),
            ttl_seconds=TTL_FAST_SECONDS,
            description="Canonical raw chain sum of vanna sensitivities; not position-weighted exposure",
            tags=["gex", "vanna", "sensitivity", "canonical"],
        ),
        FeatureSpec(
            name="net_vanna",
            extractor=lambda s: _get_agg_first(s, ("net_vanna_raw_sum", "net_vanna"), 0.0),
            ttl_seconds=TTL_FAST_SECONDS,
            description="Legacy alias of net_vanna_raw_sum",
            tags=["gex", "vanna", "sensitivity"],
        ),
    ]


def _build_vrp_and_impact_specs(bundle: _ExtractorBundle) -> list[FeatureSpec]:
    return [
        FeatureSpec(
            name="vol_risk_premium",
            extractor=lambda s: _safe(lambda: compute_vrp(_get_agg(s, "atm_iv", 0.0), settings.vrp_baseline_hv)),
            ttl_seconds=TTL_FAST_SECONDS,
            description="ATM IV minus baseline HV in percent points (decimal/percent baseline auto-normalized)",
            tags=["iv", "regime", "vrp"],
        ),
        FeatureSpec(
            name="vrp_realized_based",
            extractor=bundle.vrp_realized_based,
            ttl_seconds=TTL_FAST_SECONDS,
            description="Research-path VRP in percent points using rolling realized volatility baseline",
            tags=["iv", "research", "vrp", "canonical"],
        ),
        FeatureSpec(
            name="peak_impact",
            extractor=bundle.max_impact,
            ttl_seconds=TTL_FAST_SECONDS,
            description="Peak institutional impact index proxy (max flow * gamma)",
            tags=["institutional", "threat"],
        ),
    ]


def build_default_extractors() -> list[FeatureSpec]:
    """Build the pre-defined feature specs for L2."""
    bundle = _build_bundle()
    specs: list[FeatureSpec] = []
    specs.extend(_build_core_specs(bundle))
    specs.extend(_build_skew_specs(bundle))
    specs.extend(_build_volatility_specs(bundle))
    specs.extend(_build_sensitivity_specs())
    specs.extend(_build_vrp_and_impact_specs(bundle))
    return specs


def reset_all_default_extractors(specs: list[FeatureSpec]) -> None:
    """Call reset() on any stateful extractors in a spec list."""
    for spec in specs:
        if hasattr(spec.extractor, "reset"):
            spec.extractor.reset()

"""Schemas and field contracts for the research feature store."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pyarrow as pa

_VALID_VIEWS = {"compact", "feature", "audit"}
_VALID_INTERVALS = {"1s": 1, "5s": 5, "1m": 60}
_VALID_FORMATS = {"jsonl", "parquet"}

_COMPACT_FIELDS = {
    "data_timestamp",
    "as_of_utc",
    "l0_version",
    "symbol",
    "spot",
    "atm_iv",
    "net_gex",
    "call_wall",
    "put_wall",
    "flip_level",
    "direction",
    "confidence",
    "gex_intensity",
    "iv_regime",
    "vpin_composite",
    "bbo_imbalance_raw",
    "vol_accel_ratio",
    "mtf_consensus",
    "mtf_alignment",
    "mtf_strength",
    "dealer_squeeze_alert",
}

_FEATURE_BASE_FIELDS = {
    "data_timestamp",
    "as_of_utc",
    "l0_version",
    "symbol",
    "spot",
    "atm_iv",
    "skew_25d_normalized",
    "rr25_call_minus_put",
    "realized_volatility_15m",
    "vol_risk_premium",
    "vrp_realized_based",
    "longport_tier2_contracts",
    "longport_tier3_contracts",
    "longport_tier2_standard_ratio",
    "longport_tier3_standard_ratio",
    "longport_tier2_avg_premium",
    "longport_tier3_avg_premium",
    "longport_official_hv_decimal",
    "longport_official_hv_sample_count",
    "longport_official_hv_age_sec",
    "vrp_official_hv_based",
    "net_gex",
    "net_vanna_raw_sum",
    "net_vanna",
    "net_charm_raw_sum",
    "net_charm",
    "call_wall",
    "put_wall",
    "flip_level",
    "vpin_1m",
    "vpin_5m",
    "vpin_15m",
    "vpin_composite",
    "bbo_imbalance_raw",
    "bbo_ewma_fast",
    "bbo_ewma_slow",
    "bbo_persistence",
    "vol_accel_ratio",
    "vol_accel_threshold",
    "vol_accel_elevated",
    "vol_entropy",
    "session_phase",
    "mtf_consensus",
    "mtf_alignment",
    "mtf_strength",
    "direction",
    "confidence",
    "pre_guard_direction",
    "guard_actions_json",
    "fusion_weights_json",
    "signal_summary_json",
    "feature_vector_json",
    "iv_regime",
    "gex_intensity",
    "max_impact",
    "dealer_squeeze_alert",
    "stored_at",
}

_LABEL_FIELDS = {
    "data_timestamp",
    "l0_version",
    "symbol",
    "fwd_ret_1m",
    "fwd_ret_5m",
    "fwd_ret_15m",
    "fwd_ret_60m",
    "max_adverse_excursion",
    "realized_vol_horizon",
    "horizon_observed_seconds",
    "stored_at",
}


@dataclass
class _PendingOutcome:
    ts: datetime
    l0_version: int
    symbol: str
    base_spot: float
    last_spot: float
    min_ret: float = 0.0
    max_ret: float = 0.0
    log_returns: list[float] = field(default_factory=list)
    fwd_ret: dict[str, float | None] = field(
        default_factory=lambda: {"1m": None, "5m": None, "15m": None, "60m": None}
    )


def raw_schema() -> pa.Schema:
    return pa.schema(
        [
            ("data_timestamp", pa.string()),
            ("as_of_utc", pa.string()),
            ("l0_version", pa.int64()),
            ("symbol", pa.string()),
            ("spot", pa.float64()),
            ("atm_iv", pa.float64()),
            ("net_gex", pa.float64()),
            ("net_vanna_raw_sum", pa.float64()),
            ("net_vanna", pa.float64()),
            ("net_charm_raw_sum", pa.float64()),
            ("net_charm", pa.float64()),
            ("call_wall", pa.float64()),
            ("put_wall", pa.float64()),
            ("flip_level", pa.float64()),
            ("vpin_1m", pa.float64()),
            ("vpin_5m", pa.float64()),
            ("vpin_15m", pa.float64()),
            ("vpin_composite", pa.float64()),
            ("bbo_imbalance_raw", pa.float64()),
            ("bbo_ewma_fast", pa.float64()),
            ("bbo_ewma_slow", pa.float64()),
            ("bbo_persistence", pa.float64()),
            ("vol_accel_ratio", pa.float64()),
            ("vol_accel_threshold", pa.float64()),
            ("vol_accel_elevated", pa.bool_()),
            ("vol_entropy", pa.float64()),
            ("session_phase", pa.string()),
            ("mtf_consensus", pa.string()),
            ("mtf_alignment", pa.float64()),
            ("mtf_strength", pa.float64()),
            ("stored_at", pa.string()),
        ]
    )


def feature_schema() -> pa.Schema:
    return pa.schema(
        [
            *raw_schema(),
            ("skew_25d_normalized", pa.float64()),
            ("rr25_call_minus_put", pa.float64()),
            ("realized_volatility_15m", pa.float64()),
            ("vol_risk_premium", pa.float64()),
            ("vrp_realized_based", pa.float64()),
            ("longport_tier2_contracts", pa.int64()),
            ("longport_tier3_contracts", pa.int64()),
            ("longport_tier2_standard_ratio", pa.float64()),
            ("longport_tier3_standard_ratio", pa.float64()),
            ("longport_tier2_avg_premium", pa.float64()),
            ("longport_tier3_avg_premium", pa.float64()),
            ("longport_official_hv_decimal", pa.float64()),
            ("longport_official_hv_sample_count", pa.int64()),
            ("longport_official_hv_age_sec", pa.float64()),
            ("vrp_official_hv_based", pa.float64()),
            ("direction", pa.string()),
            ("confidence", pa.float64()),
            ("pre_guard_direction", pa.string()),
            ("guard_actions_json", pa.string()),
            ("fusion_weights_json", pa.string()),
            ("signal_summary_json", pa.string()),
            ("feature_vector_json", pa.string()),
            ("iv_regime", pa.string()),
            ("gex_intensity", pa.string()),
            ("max_impact", pa.float64()),
            ("dealer_squeeze_alert", pa.bool_()),
        ]
    )


def label_schema() -> pa.Schema:
    return pa.schema(
        [
            ("data_timestamp", pa.string()),
            ("l0_version", pa.int64()),
            ("symbol", pa.string()),
            ("fwd_ret_1m", pa.float64()),
            ("fwd_ret_5m", pa.float64()),
            ("fwd_ret_15m", pa.float64()),
            ("fwd_ret_60m", pa.float64()),
            ("max_adverse_excursion", pa.float64()),
            ("realized_vol_horizon", pa.float64()),
            ("horizon_observed_seconds", pa.float64()),
            ("stored_at", pa.string()),
        ]
    )


def tier_schema(tier_name: str) -> pa.Schema:
    if tier_name == "raw":
        return raw_schema()
    if tier_name == "feature":
        return feature_schema()
    if tier_name == "label":
        return label_schema()
    raise ValueError(f"unknown tier schema: {tier_name}")

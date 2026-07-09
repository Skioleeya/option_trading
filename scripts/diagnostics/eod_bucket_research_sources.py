from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

RAW_COLUMNS = [
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
    "bbo_imbalance_raw",
    "session_phase",
    "stored_at",
]
FEATURE_COLUMNS = [
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
    "bbo_imbalance_raw",
    "session_phase",
    "skew_25d_normalized",
    "rr25_call_minus_put",
    "realized_volatility_15m",
    "vol_risk_premium",
    "vrp_realized_based",
    "longport_official_hv_decimal",
    "longport_official_hv_sample_count",
    "longport_official_hv_age_sec",
    "vrp_official_hv_based",
    "direction_code",
    "iv_regime_code",
    "gex_intensity_code",
    "confidence",
    "max_impact",
    "dealer_squeeze_alert",
    "net_delta_exposure_live",
    "net_gamma_exposure_live",
    "residual_delta_after_netting",
    "oi_participation_ratio_live",
    "flow_suppression_bias",
    "flow_dominance_ratio",
    "midpoint_tickrule_count",
    "condition_filtered_count",
    "complex_spread_count",
    "stored_at",
]
LABEL_COLUMNS = [
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
]


def project_research_sources_from_canonical(
    *,
    canonical_path: Path,
    frozen_root: Path,
    final_daily_dir: Path,
    date_str: str,
) -> tuple[list[dict[str, Any]], dict[str, int], Path]:
    table = pq.read_table(canonical_path)
    label_table = (
        table.filter(table.column("horizon_observed_seconds").is_valid())
        .select(
            [
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
                "label_stored_at",
            ]
        )
        .rename_columns(LABEL_COLUMNS)
    )
    projections = {
        "research_raw": table.select(RAW_COLUMNS),
        "research_feature": table.select(FEATURE_COLUMNS),
        "research_label": label_table,
    }
    outputs: list[dict[str, Any]] = []
    rows_by_role: dict[str, int] = {}
    raw_stage_path = frozen_root / "sources" / "research_raw" / f"raw_{date_str}.parquet"
    for role, projected in projections.items():
        file_name = {
            "research_raw": f"raw_{date_str}.parquet",
            "research_feature": f"feature_{date_str}.parquet",
            "research_label": f"label_{date_str}.parquet",
        }[role]
        stage_path = frozen_root / "sources" / role / file_name
        stage_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(projected, stage_path)
        outputs.append(
            {
                "role": role,
                "path": (final_daily_dir / "sources" / role / file_name).as_posix(),
                "source_path": canonical_path.as_posix(),
                "size_bytes": stage_path.stat().st_size,
                "sha256": sha256_file(stage_path),
            }
        )
        rows_by_role[role] = projected.num_rows
        if role == "research_raw":
            raw_stage_path = stage_path
    return outputs, rows_by_role, raw_stage_path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

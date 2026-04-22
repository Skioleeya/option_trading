"""Metadata helpers used by the compute loop orchestration path."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.loops.mm_flow_metadata import build_mm_flow_metrics


def _coerce_utc_datetime(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_volume_map(raw: Any) -> dict[str, float]:
    """Normalize volume_map into a JSON-safe strike->volume dict."""
    if not isinstance(raw, dict):
        return {}

    out: dict[str, float] = {}
    for strike, volume in raw.items():
        try:
            strike_f = float(strike)
            volume_f = float(volume)
        except (TypeError, ValueError):
            continue
        if strike_f <= 0 or volume_f < 0:
            continue
        out[str(strike)] = volume_f
    return out


def _normalize_source_timestamp_utc(snapshot: dict[str, Any]) -> str | None:
    """Normalize L0 source timestamp to UTC ISO8601."""
    raw = snapshot.get("as_of_utc")
    if raw is None:
        raw = snapshot.get("as_of")
    dt = _coerce_utc_datetime(raw)
    if dt is None:
        return None
    return dt.isoformat()


def _build_l1_extra_metadata(
    snapshot: dict[str, Any],
    compute_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the L0->L1 metadata pass-through contract."""
    mm_flow_metrics = build_mm_flow_metrics(snapshot)
    metadata = {
        "rust_active": snapshot.get("rust_active", False),
        "shm_stats": snapshot.get("shm_stats"),
        "governor_telemetry": dict(snapshot.get("governor_telemetry") or {}),
        "volume_map": _normalize_volume_map(snapshot.get("volume_map")),
        "source_data_timestamp_utc": _normalize_source_timestamp_utc(snapshot),
        "longport_option_diagnostics": _build_longport_option_diagnostics(snapshot),
        "header_volatility_aux": dict(snapshot.get("header_volatility_aux_diagnostics") or {}),
        "mm_flow_metrics": mm_flow_metrics,
    }
    if compute_audit:
        metadata["compute_audit"] = dict(compute_audit)
    return metadata


def _build_longport_option_diagnostics(
    snapshot: dict[str, Any],
) -> dict[str, float | int | str | None]:
    """Summarize official LongPort premium/standard diagnostics from Tier2/Tier3 caches."""
    diag: dict[str, float | int | str | None] = {
        "tier2_contracts": _count_rows(snapshot.get("tier2_chain")),
        "tier3_contracts": _count_rows(snapshot.get("tier3_chain")),
        "tier2_standard_ratio": _standard_ratio(snapshot.get("tier2_chain")),
        "tier3_standard_ratio": _standard_ratio(snapshot.get("tier3_chain")),
        "tier2_avg_premium": _average_numeric(snapshot.get("tier2_chain"), "premium"),
        "tier3_avg_premium": _average_numeric(snapshot.get("tier3_chain"), "premium"),
    }
    official = snapshot.get("official_hv_diagnostics")
    official_hv_decimal: float | None = None
    official_hv_sample_count = 0
    official_hv_synced_at_utc: str | None = None
    official_hv_age_sec: float | None = None
    official_hv_synced_dt: datetime | None = None

    if isinstance(official, dict):
        raw_hv = official.get("official_hv_decimal")
        try:
            hv_val = float(raw_hv)
        except (TypeError, ValueError):
            hv_val = None
        if hv_val is not None and math.isfinite(hv_val) and hv_val > 0.0:
            official_hv_decimal = hv_val

        raw_count = official.get("official_hv_sample_count")
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            count = 0
        official_hv_sample_count = max(0, count)

        official_hv_synced_dt = _coerce_utc_datetime(
            official.get("official_hv_synced_at_utc")
        )
        if official_hv_synced_dt is not None:
            official_hv_synced_at_utc = official_hv_synced_dt.isoformat()

    source_dt = _coerce_utc_datetime(snapshot.get("as_of_utc") or snapshot.get("as_of"))
    if source_dt is not None and official_hv_synced_dt is not None:
        official_hv_age_sec = max(
            0.0,
            (source_dt - official_hv_synced_dt).total_seconds(),
        )

    diag.update(
        {
            "official_hv_decimal": official_hv_decimal,
            "official_hv_sample_count": official_hv_sample_count,
            "official_hv_synced_at_utc": official_hv_synced_at_utc,
            "official_hv_age_sec": official_hv_age_sec,
        }
    )
    return diag


def _count_rows(rows: Any) -> int:
    if not isinstance(rows, list):
        return 0
    return len(rows)


def _standard_ratio(rows: Any) -> float:
    if not isinstance(rows, list) or not rows:
        return 0.0
    standard_flags = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        standard_flags.append(1 if bool(row.get("standard", False)) else 0)
    if not standard_flags:
        return 0.0
    return sum(standard_flags) / len(standard_flags)


def _average_numeric(rows: Any, key: str) -> float:
    if not isinstance(rows, list) or not rows:
        return 0.0
    values: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = row.get(key)
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            values.append(value)
    if not values:
        return 0.0
    return sum(values) / len(values)

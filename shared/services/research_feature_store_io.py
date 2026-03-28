"""I/O and query helpers for the research feature store."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from shared.services.research_feature_store_schema import (
    _COMPACT_FIELDS,
    _FEATURE_BASE_FIELDS,
    _LABEL_FIELDS,
    _VALID_INTERVALS,
)
from shared.services.research_feature_store_utils import _ET, coerce_timestamp, in_range, iter_trade_dates

logger = logging.getLogger(__name__)


def enqueue_export(store: Any, *, records: list[dict[str, Any]], fmt: str) -> str:
    job_id = uuid.uuid4().hex
    suffix = ".parquet" if fmt == "parquet" else ".jsonl"
    path = store._export_dir / f"{job_id}{suffix}"
    store._jobs[job_id] = {"status": "pending", "path": str(path), "format": fmt}
    asyncio.create_task(run_export_job(store, job_id=job_id, path=path, records=records, fmt=fmt))
    return job_id


async def run_export_job(
    store: Any,
    *,
    job_id: str,
    path: Path,
    records: list[dict[str, Any]],
    fmt: str,
) -> None:
    try:
        if fmt == "parquet":
            path.write_bytes(records_to_parquet(records))
        else:
            with path.open("w", encoding="utf-8") as fh:
                for row in records:
                    fh.write(json.dumps(row, ensure_ascii=True))
                    fh.write("\n")
        store._jobs[job_id] = {"status": "done", "path": str(path), "format": fmt}
    except Exception as exc:
        logger.error("[ResearchFeatureStore] export job failed id=%s error=%s", job_id, exc)
        store._jobs[job_id] = {"status": "failed", "path": str(path), "format": fmt, "error": str(exc)}


def query_records(
    store: Any,
    *,
    start_dt: datetime,
    end_dt: datetime,
    view: str,
    fields: list[str] | None,
    interval: str,
) -> list[dict[str, Any]] | dict[str, Any]:
    records = load_feature_range(store, start_dt=start_dt, end_dt=end_dt)
    if view == "compact":
        records = [to_compact_record(r) for r in records]
    else:
        labels = load_label_map(store, start_dt=start_dt, end_dt=end_dt)
        if labels:
            for row in records:
                key = (str(row.get("data_timestamp", "")), int(row.get("l0_version", 0)))
                label_row = labels.get(key)
                if label_row:
                    row.update(label_row)
    if fields:
        projected = project_fields(store, records, view=view, fields=fields)
        if isinstance(projected, dict):
            return projected
        records = projected
    return apply_interval(records, interval=interval)


def project_fields(
    store: Any,
    records: list[dict[str, Any]],
    *,
    view: str,
    fields: list[str],
) -> list[dict[str, Any]] | dict[str, Any]:
    requested = [f.strip() for f in fields if f and f.strip()]
    if not requested:
        return records
    if len(requested) > store._max_fields_per_query:
        return {"error": f"too many fields requested: {len(requested)} > {store._max_fields_per_query}"}

    allowed = _COMPACT_FIELDS if view == "compact" else _FEATURE_BASE_FIELDS | _LABEL_FIELDS
    unknown = [f for f in requested if f not in allowed]
    if unknown:
        return {"error": f"unknown fields: {','.join(sorted(unknown))}"}
    return [{k: row.get(k) for k in requested} for row in records]


def apply_interval(records: list[dict[str, Any]], *, interval: str) -> list[dict[str, Any]]:
    step = _VALID_INTERVALS[interval]
    if step <= 1 or not records:
        return records

    out: list[dict[str, Any]] = []
    last_bucket: int | None = None
    last_direction: str | None = None
    for row in sorted(records, key=lambda r: str(r.get("data_timestamp", ""))):
        ts = coerce_timestamp(row.get("data_timestamp"))
        if ts is None:
            continue
        direction = str(row.get("direction", ""))
        event_keep = last_direction is not None and direction != last_direction
        bucket = int(ts.timestamp() // step)
        if event_keep or bucket != last_bucket:
            out.append(row)
            last_bucket = bucket
            last_direction = direction
    return out


def load_feature_range(store: Any, *, start_dt: datetime, end_dt: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for date_str in iter_trade_dates(start_dt, end_dt):
        path = store._feature_dir / f"feature_{date_str}.parquet"
        if not path.exists():
            continue
        try:
            rows.extend(pq.read_table(path).to_pylist())
        except Exception as exc:
            logger.error("[ResearchFeatureStore] feature read failed path=%s error=%s", path.name, exc)
    return [r for r in rows if in_range(coerce_timestamp(r.get("data_timestamp")), start_dt, end_dt)]


def load_label_map(store: Any, *, start_dt: datetime, end_dt: datetime) -> dict[tuple[str, int], dict[str, Any]]:
    out: dict[tuple[str, int], dict[str, Any]] = {}
    for date_str in iter_trade_dates(start_dt, end_dt):
        path = store._label_dir / f"label_{date_str}.parquet"
        if not path.exists():
            continue
        try:
            rows = pq.read_table(path).to_pylist()
        except Exception as exc:
            logger.error("[ResearchFeatureStore] label read failed path=%s error=%s", path.name, exc)
            continue
        for row in rows:
            ts = coerce_timestamp(row.get("data_timestamp"))
            if not in_range(ts, start_dt, end_dt):
                continue
            key = (str(row.get("data_timestamp", "")), int(row.get("l0_version", 0)))
            out[key] = {
                "fwd_ret_1m": row.get("fwd_ret_1m"),
                "fwd_ret_5m": row.get("fwd_ret_5m"),
                "fwd_ret_15m": row.get("fwd_ret_15m"),
                "fwd_ret_60m": row.get("fwd_ret_60m"),
                "max_adverse_excursion": row.get("max_adverse_excursion"),
                "realized_vol_horizon": row.get("realized_vol_horizon"),
                "horizon_observed_seconds": row.get("horizon_observed_seconds"),
            }
    return out


def load_latest_feature(store: Any, *, count: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    files = sorted(store._feature_dir.glob("feature_*.parquet"), reverse=True)
    for path in files:
        try:
            rows.extend(pq.read_table(path).to_pylist())
        except Exception as exc:
            logger.error("[ResearchFeatureStore] latest feature read failed path=%s error=%s", path.name, exc)
            continue
        if len(rows) >= count:
            break
    rows.sort(key=lambda r: str(r.get("data_timestamp", "")))
    return rows[-count:] if count > 0 else []


def cleanup_retention_if_needed(store: Any, date_str: str) -> None:
    if store._last_cleanup_date == date_str:
        return
    store._last_cleanup_date = date_str
    now_et = datetime.now(_ET).date()
    cleanup_tier(store._raw_dir, "raw", now_et, store._raw_retention_days)
    cleanup_tier(store._feature_dir, "feature", now_et, store._feature_retention_days)
    cleanup_tier(store._label_dir, "label", now_et, store._label_retention_days)


def cleanup_tier(tier_dir: Path, prefix: str, now_et_date: Any, retention_days: int) -> None:
    cutoff = now_et_date - timedelta(days=max(1, retention_days))
    for path in tier_dir.glob(f"{prefix}_*.parquet"):
        date_part = path.stem.split("_")[-1]
        if len(date_part) != 8 or not date_part.isdigit():
            continue
        try:
            file_date = datetime.strptime(date_part, "%Y%m%d").date()
        except ValueError:
            continue
        if file_date >= cutoff:
            continue
        try:
            os.remove(path)
        except OSError as exc:
            logger.error("[ResearchFeatureStore] retention delete failed path=%s error=%s", path.name, exc)


def to_compact_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_timestamp": row.get("data_timestamp"),
        "as_of_utc": row.get("as_of_utc"),
        "l0_version": row.get("l0_version"),
        "symbol": row.get("symbol"),
        "spot": row.get("spot"),
        "atm_iv": row.get("atm_iv"),
        "net_gex": row.get("net_gex"),
        "call_wall": row.get("call_wall"),
        "put_wall": row.get("put_wall"),
        "flip_level": row.get("flip_level"),
        "direction": row.get("direction"),
        "confidence": row.get("confidence"),
        "gex_intensity": row.get("gex_intensity"),
        "iv_regime": row.get("iv_regime"),
        "vpin_composite": row.get("vpin_composite"),
        "bbo_imbalance_raw": row.get("bbo_imbalance_raw"),
        "vol_accel_ratio": row.get("vol_accel_ratio"),
        "mtf_consensus": row.get("mtf_consensus"),
        "mtf_alignment": row.get("mtf_alignment"),
        "mtf_strength": row.get("mtf_strength"),
        "dealer_squeeze_alert": row.get("dealer_squeeze_alert"),
    }


def records_to_parquet(records: list[dict[str, Any]]) -> bytes:
    table = pa.Table.from_pylist(records)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression="zstd", use_dictionary=True)
    return sink.getvalue().to_pybytes()

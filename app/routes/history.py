"""Historical data endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from shared.config import settings

router = APIRouter()

_UTC = timezone.utc


def _parse_fields(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    out = [f.strip() for f in raw.split(",") if f.strip()]
    return out or None


def _coerce_timestamp(raw: Any) -> datetime | None:
    if raw is None:
        return None
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
        return dt.replace(tzinfo=_UTC)
    return dt.astimezone(_UTC)


def _to_finite_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def _compact_from_warm_payload(row: dict[str, Any]) -> dict[str, Any]:
    agent_data = ((row.get("agent_g") or {}).get("data") or {})
    signal_summary = agent_data.get("signal_summary", {})
    gamma_walls = agent_data.get("gamma_walls") or {}
    micro = agent_data.get("micro_structure", {})
    micro_state = micro.get("micro_structure_state", {}) if isinstance(micro, dict) else {}
    mtf = micro_state.get("mtf_consensus") if isinstance(micro_state, dict) else {}
    if not isinstance(mtf, dict):
        mtf = {}
    return {
        "data_timestamp": row.get("data_timestamp") or row.get("timestamp"),
        "as_of_utc": row.get("data_timestamp") or row.get("timestamp"),
        "l0_version": int(agent_data.get("version", row.get("version", 0)) or 0),
        "symbol": "SPY",
        "spot": _to_finite_float(row.get("spot"), 0.0),
        "atm_iv": _to_finite_float(agent_data.get("spy_atm_iv"), 0.0),
        "net_gex": _to_finite_float(agent_data.get("net_gex"), 0.0),
        "call_wall": _to_finite_float(gamma_walls.get("call_wall"), 0.0),
        "put_wall": _to_finite_float(gamma_walls.get("put_wall"), 0.0),
        "flip_level": _to_finite_float(agent_data.get("gamma_flip_level"), 0.0),
        "direction": str(agent_data.get("direction", "NEUTRAL")),
        "confidence": _to_finite_float(agent_data.get("confidence"), 0.0),
        "gex_intensity": str(signal_summary.get("gex_intensity", "NEUTRAL")),
        "iv_regime": str(signal_summary.get("iv_regime", "NORMAL")),
        "vpin_composite": _to_finite_float(signal_summary.get("raw_vpin"), 0.0),
        "bbo_imbalance_raw": _to_finite_float(signal_summary.get("raw_bbo_imb"), 0.0),
        "vol_accel_ratio": _to_finite_float(signal_summary.get("raw_vol_accel"), 0.0),
        "mtf_consensus": str(mtf.get("consensus", "NEUTRAL")),
        "mtf_alignment": _to_finite_float(mtf.get("alignment"), 0.0),
        "mtf_strength": _to_finite_float(mtf.get("strength"), 0.0),
        "dealer_squeeze_alert": bool(micro_state.get("dealer_squeeze_alert", False)) if isinstance(micro_state, dict) else False,
    }


def _apply_interval(rows: list[dict[str, Any]], interval: str) -> list[dict[str, Any]]:
    steps = {"1s": 1, "5s": 5, "1m": 60}
    step = steps.get(interval, 1)
    if step <= 1:
        return rows
    out: list[dict[str, Any]] = []
    last_bucket: int | None = None
    last_direction: str | None = None
    for row in sorted(rows, key=lambda r: str(r.get("data_timestamp", ""))):
        ts = _coerce_timestamp(row.get("data_timestamp"))
        if ts is None:
            continue
        direction = str(row.get("direction", ""))
        event_change = last_direction is not None and direction != last_direction
        bucket = int(ts.timestamp() // step)
        if event_change or bucket != last_bucket:
            out.append(row)
            last_bucket = bucket
            last_direction = direction
    return out


def _project_fields(rows: list[dict[str, Any]], fields: list[str] | None) -> list[dict[str, Any]]:
    if not fields:
        return rows
    if len(fields) > int(settings.history_max_fields_per_query):
        raise HTTPException(
            status_code=400,
            detail=f"too many fields requested: {len(fields)} > {settings.history_max_fields_per_query}",
        )
    return [{k: row.get(k) for k in fields} for row in rows]


def _to_parquet_bytes(rows: list[dict[str, Any]]) -> bytes:
    table = pa.Table.from_pylist(rows)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression="zstd", use_dictionary=True)
    return sink.getvalue().to_pybytes()


@router.get("/history")
async def get_history(
    request: Request,
    count: int = 50,
    view: str = Query(default=settings.history_default_view),
    fields: str | None = None,
    interval: str = "1s",
    format: str = "jsonl",
):
    """Retrieve historical snapshots with projection-first views."""
    container = request.app.state.container
    count = max(1, min(count, int(settings.history_max_points_per_query)))
    view_norm = (view or settings.history_default_view).strip().lower()
    fmt_norm = format.strip().lower()
    if fmt_norm not in {"jsonl", "parquet"}:
        raise HTTPException(status_code=400, detail=f"invalid format: {format}")

    field_list = _parse_fields(fields)
    rows: list[dict[str, Any]]

    if view_norm == "compact":
        if container.l3_reactor:
            history = await container.l3_reactor.store.get_warm_latest(count)
        else:
            history = await container.historical_store.get_latest(count)
        rows = [_compact_from_warm_payload(h) for h in history]
    elif view_norm == "feature":
        if not container.l3_reactor:
            raise HTTPException(status_code=503, detail="l3 reactor unavailable")
        rows = container.l3_reactor.research_store.latest_feature_view(
            count=count,
            view="feature",
            fields=field_list,
        )
        field_list = None
    elif view_norm == "audit":
        rows = [entry.to_dict() for entry in container.l2_reactor.audit.recent(count)]
    elif view_norm == "full":
        if container.l3_reactor:
            rows = await container.l3_reactor.store.get_warm_latest(count)
        else:
            rows = await container.historical_store.get_latest(count)
    else:
        raise HTTPException(status_code=400, detail=f"invalid view: {view}")

    rows = _apply_interval(rows, interval=interval)
    rows = _project_fields(rows, field_list)

    if fmt_norm == "parquet":
        return Response(content=_to_parquet_bytes(rows), media_type="application/x-parquet")
    return {"history": rows, "count": len(rows), "view": view_norm, "format": "jsonl"}


@router.get("/api/research/features")
async def get_research_features(
    request: Request,
    start: str,
    end: str,
    fields: str | None = None,
    view: str = "feature",
    interval: str = "1s",
    format: str = "jsonl",
):
    """Query research feature store with field projection and compact format options."""
    container = request.app.state.container
    if not container.l3_reactor:
        raise HTTPException(status_code=503, detail="l3 reactor unavailable")

    result = await container.l3_reactor.research_store.query(
        start=start,
        end=end,
        fields=_parse_fields(fields),
        view=view,
        interval=interval,
        fmt=format,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    if result.get("status") == "accepted":
        return result
    if result.get("format") == "parquet":
        return Response(content=result["bytes"], media_type=result["content_type"])
    return result


@router.get("/api/research/exports/{job_id}")
async def get_research_export_status(request: Request, job_id: str):
    container = request.app.state.container
    if not container.l3_reactor:
        raise HTTPException(status_code=503, detail="l3 reactor unavailable")
    job = await container.l3_reactor.research_store.get_export_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job_id, **job}


@router.get("/api/research/exports/{job_id}/download")
async def download_research_export(request: Request, job_id: str):
    container = request.app.state.container
    if not container.l3_reactor:
        raise HTTPException(status_code=503, detail="l3 reactor unavailable")
    payload = await container.l3_reactor.research_store.read_export(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="export not ready")
    content_type, data = payload
    return Response(content=data, media_type=content_type)


@router.get("/api/atm-decay/history")
async def get_atm_decay_history(request: Request):
    """Retrieve the full historical ATM decay series for the current trade date."""
    container = request.app.state.container
    date_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
    history = await container.atm_decay_tracker.get_history(date_str)

    return {
        "date": date_str,
        "history": history,
        "count": len(history)
    }


@router.post("/api/atm-decay/flush-history")
async def flush_atm_decay_history(request: Request):
    """Flush and rebuild the ATM decay history from the Intraday API."""
    container = request.app.state.container
    date_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
    await container.atm_decay_tracker.flush_and_rebuild()
    history = await container.atm_decay_tracker.get_history(date_str)

    return {
        "date": date_str,
        "message": "History flushed and rebuilt",
        "history": history,
        "count": len(history)
    }

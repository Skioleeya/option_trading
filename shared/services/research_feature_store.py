"""Research feature store for strategy R&D and parameter tuning."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq

from shared.config import settings

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")
_UTC = timezone.utc
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
    "net_gex",
    "net_vanna",
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


class ResearchFeatureStore:
    """Three-tier research persistence and query service."""

    def __init__(
        self,
        *,
        root_dir: str | Path | None = None,
        raw_retention_days: int | None = None,
        feature_retention_days: int | None = None,
        label_retention_days: int | None = None,
    ) -> None:
        self._root = Path(root_dir or settings.research_store_root)
        self._raw_dir = self._root / "raw"
        self._feature_dir = self._root / "feature"
        self._label_dir = self._root / "label"
        self._export_dir = self._root / "exports"
        for p in (self._raw_dir, self._feature_dir, self._label_dir, self._export_dir):
            p.mkdir(parents=True, exist_ok=True)

        self._raw_retention_days = int(raw_retention_days or settings.research_raw_retention_days)
        self._feature_retention_days = int(
            feature_retention_days or settings.research_feature_retention_days
        )
        self._label_retention_days = int(label_retention_days or settings.research_label_retention_days)

        self._max_fields_per_query = int(settings.history_max_fields_per_query)
        self._max_points_per_query = int(settings.history_max_points_per_query)

        self._pending_labels: dict[tuple[str, int, str], _PendingOutcome] = {}
        self._last_cleanup_date: str | None = None

        self._last_sample_bucket_5s: int | None = None
        self._last_direction: str | None = None
        self._last_net_gex: float | None = None

        self._horizons = {"1m": 60.0, "5m": 300.0, "15m": 900.0, "60m": 3600.0}
        self._max_horizon_seconds = max(self._horizons.values())

        self._jobs: dict[str, dict[str, Any]] = {}

    def append_tick(self, *, decision: Any, snapshot: Any, payload: Any) -> None:
        """Append current tick to raw/feature tables and update outcome labels."""
        ts = self._coerce_timestamp(getattr(payload, "data_timestamp", None))
        if ts is None:
            ts = datetime.now(_UTC)

        spot = self._to_float(getattr(snapshot, "spot", getattr(payload, "spot", None)))
        if spot is None or spot <= 0.0:
            return

        symbol = "SPY"
        l0_version = self._coerce_int(getattr(snapshot, "version", getattr(payload, "version", 0)), 0)
        as_of_utc = self._extract_as_of_utc(snapshot, payload, ts)
        store_date = ts.astimezone(_ET).strftime("%Y%m%d")

        self._cleanup_retention_if_needed(store_date)
        self._update_pending_labels(ts=ts, spot=spot, symbol=symbol, version=l0_version)

        key = (ts.isoformat(), l0_version, symbol)
        if key not in self._pending_labels:
            self._pending_labels[key] = _PendingOutcome(
                ts=ts,
                l0_version=l0_version,
                symbol=symbol,
                base_spot=spot,
                last_spot=spot,
            )

        aggregates = getattr(snapshot, "aggregates", None)
        micro = getattr(snapshot, "microstructure", None)

        direction = str(getattr(decision, "direction", "NEUTRAL"))
        guard_actions = list(getattr(decision, "guard_actions", []))
        net_gex = self._to_float(getattr(aggregates, "net_gex", None), 0.0)
        event_trigger = bool(guard_actions)
        if self._last_direction is not None and direction != self._last_direction:
            event_trigger = True
        if self._last_net_gex is not None and abs(net_gex - self._last_net_gex) >= 1e8:
            event_trigger = True

        bucket_5s = int(ts.timestamp() // 5)
        sampled_5s = self._last_sample_bucket_5s is None or bucket_5s != self._last_sample_bucket_5s
        if sampled_5s:
            self._last_sample_bucket_5s = bucket_5s

        self._last_direction = direction
        self._last_net_gex = net_gex

        if not (event_trigger or sampled_5s):
            return

        mtf = self._coerce_dict(getattr(micro, "mtf_consensus", None))
        raw_row = {
            "data_timestamp": ts.isoformat(),
            "as_of_utc": as_of_utc,
            "l0_version": l0_version,
            "symbol": symbol,
            "spot": self._f32(spot),
            "atm_iv": self._f32(self._to_float(getattr(aggregates, "atm_iv", None), 0.0)),
            "net_gex": self._f32(net_gex),
            "net_vanna": self._f32(self._to_float(getattr(aggregates, "net_vanna", None), 0.0)),
            "net_charm": self._f32(self._to_float(getattr(aggregates, "net_charm", None), 0.0)),
            "call_wall": self._f32(self._to_float(getattr(aggregates, "call_wall", None), 0.0)),
            "put_wall": self._f32(self._to_float(getattr(aggregates, "put_wall", None), 0.0)),
            "flip_level": self._f32(self._to_float(getattr(aggregates, "flip_level", None), 0.0)),
            "vpin_1m": self._f32(self._to_float(getattr(micro, "vpin_1m", None), 0.0)),
            "vpin_5m": self._f32(self._to_float(getattr(micro, "vpin_5m", None), 0.0)),
            "vpin_15m": self._f32(self._to_float(getattr(micro, "vpin_15m", None), 0.0)),
            "vpin_composite": self._f32(self._to_float(getattr(micro, "vpin_composite", None), 0.0)),
            "bbo_imbalance_raw": self._f32(self._to_float(getattr(micro, "bbo_imbalance_raw", None), 0.0)),
            "bbo_ewma_fast": self._f32(self._to_float(getattr(micro, "bbo_ewma_fast", None), 0.0)),
            "bbo_ewma_slow": self._f32(self._to_float(getattr(micro, "bbo_ewma_slow", None), 0.0)),
            "bbo_persistence": self._f32(self._to_float(getattr(micro, "bbo_persistence", None), 0.0)),
            "vol_accel_ratio": self._f32(self._to_float(getattr(micro, "vol_accel_ratio", None), 0.0)),
            "vol_accel_threshold": self._f32(self._to_float(getattr(micro, "vol_accel_threshold", None), 0.0)),
            "vol_accel_elevated": bool(getattr(micro, "vol_accel_elevated", False)),
            "vol_entropy": self._f32(self._to_float(getattr(micro, "vol_entropy", None), 0.0)),
            "session_phase": str(getattr(micro, "session_phase", "")),
            "mtf_consensus": str(mtf.get("consensus", "NEUTRAL")),
            "mtf_alignment": self._f32(self._to_float(mtf.get("alignment"), 0.0)),
            "mtf_strength": self._f32(self._to_float(mtf.get("strength"), 0.0)),
            "stored_at": datetime.now(_UTC).isoformat(),
        }

        feature_row = {
            **raw_row,
            "direction": direction,
            "confidence": self._f32(self._to_float(getattr(decision, "confidence", None), 0.0)),
            "pre_guard_direction": str(getattr(decision, "pre_guard_direction", "NEUTRAL")),
            "guard_actions_json": json.dumps(guard_actions, ensure_ascii=True),
            "fusion_weights_json": json.dumps(
                self._coerce_dict(getattr(decision, "fusion_weights", {})), ensure_ascii=True
            ),
            "signal_summary_json": json.dumps(
                self._coerce_dict(getattr(decision, "signal_summary", {})), ensure_ascii=True
            ),
            "feature_vector_json": json.dumps(
                self._coerce_dict(getattr(decision, "feature_vector", {})), ensure_ascii=True
            ),
            "iv_regime": str(getattr(decision, "iv_regime", "NORMAL") or "NORMAL"),
            "gex_intensity": str(getattr(decision, "gex_intensity", "NEUTRAL") or "NEUTRAL"),
            "max_impact": self._f32(self._to_float(getattr(decision, "max_impact", None), 0.0)),
            "dealer_squeeze_alert": bool(getattr(micro, "dealer_squeeze_alert", False)),
        }

        self._append_rows(self._raw_dir, "raw", store_date, [raw_row])
        self._append_rows(self._feature_dir, "feature", store_date, [feature_row])

    async def query(
        self,
        *,
        start: str,
        end: str,
        view: str = "feature",
        fields: list[str] | None = None,
        interval: str = "1s",
        fmt: str = "jsonl",
    ) -> dict[str, Any]:
        view_norm = view.strip().lower()
        fmt_norm = fmt.strip().lower()
        interval_norm = interval.strip().lower()
        if view_norm not in _VALID_VIEWS:
            return {"error": f"invalid view: {view}"}
        if fmt_norm not in _VALID_FORMATS:
            return {"error": f"invalid format: {fmt}"}
        if interval_norm not in _VALID_INTERVALS:
            return {"error": f"invalid interval: {interval}"}

        start_dt = self._coerce_timestamp(start)
        end_dt = self._coerce_timestamp(end)
        if start_dt is None or end_dt is None:
            return {"error": "invalid start/end timestamp"}
        if end_dt < start_dt:
            return {"error": "end must be >= start"}

        if view_norm == "audit":
            return {"error": "audit view is served by /history endpoint"}

        records = self._query_records(
            start_dt=start_dt,
            end_dt=end_dt,
            view=view_norm,
            fields=fields,
            interval=interval_norm,
        )
        if isinstance(records, dict):
            return records

        if len(records) > self._max_points_per_query:
            job_id = await self._enqueue_export(records=records, fmt=fmt_norm)
            return {
                "status": "accepted",
                "job_id": job_id,
                "count": len(records),
                "message": "Query exceeds inline limit; async export started.",
            }

        if fmt_norm == "parquet":
            return {
                "status": "ok",
                "count": len(records),
                "format": "parquet",
                "content_type": "application/x-parquet",
                "bytes": self._records_to_parquet(records),
            }
        return {"status": "ok", "count": len(records), "format": "jsonl", "records": records}

    async def get_export_job(self, job_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return dict(job)

    async def read_export(self, job_id: str) -> tuple[str, bytes] | None:
        job = self._jobs.get(job_id)
        if not job or job.get("status") != "done":
            return None
        path = Path(job["path"])
        if not path.exists():
            return None
        data = path.read_bytes()
        content_type = "application/x-parquet" if path.suffix == ".parquet" else "application/x-ndjson"
        return content_type, data

    def latest_feature_view(
        self,
        *,
        count: int,
        view: str,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        records = self._load_latest_feature(count=max(count * 4, 256))
        if view == "compact":
            records = [self._to_compact_record(r) for r in records]
        if fields:
            records_or_error = self._project_fields(records, view=view, fields=fields)
            if isinstance(records_or_error, dict):
                return []
            records = records_or_error
        return records[-count:] if count > 0 else []

    def diagnostics(self) -> dict[str, Any]:
        return {
            "root": str(self._root),
            "pending_labels": len(self._pending_labels),
            "export_jobs": len(self._jobs),
            "raw_retention_days": self._raw_retention_days,
            "feature_retention_days": self._feature_retention_days,
            "label_retention_days": self._label_retention_days,
        }

    async def _enqueue_export(self, *, records: list[dict[str, Any]], fmt: str) -> str:
        job_id = uuid.uuid4().hex
        suffix = ".parquet" if fmt == "parquet" else ".jsonl"
        path = self._export_dir / f"{job_id}{suffix}"
        self._jobs[job_id] = {"status": "pending", "path": str(path), "format": fmt}
        asyncio.create_task(self._run_export_job(job_id=job_id, path=path, records=records, fmt=fmt))
        return job_id

    async def _run_export_job(
        self,
        *,
        job_id: str,
        path: Path,
        records: list[dict[str, Any]],
        fmt: str,
    ) -> None:
        try:
            if fmt == "parquet":
                path.write_bytes(self._records_to_parquet(records))
            else:
                with path.open("w", encoding="utf-8") as fh:
                    for row in records:
                        fh.write(json.dumps(row, ensure_ascii=True))
                        fh.write("\n")
            self._jobs[job_id] = {"status": "done", "path": str(path), "format": fmt}
        except Exception as exc:
            logger.error("[ResearchFeatureStore] export job failed id=%s error=%s", job_id, exc)
            self._jobs[job_id] = {"status": "failed", "path": str(path), "format": fmt, "error": str(exc)}

    def _query_records(
        self,
        *,
        start_dt: datetime,
        end_dt: datetime,
        view: str,
        fields: list[str] | None,
        interval: str,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        records = self._load_feature_range(start_dt=start_dt, end_dt=end_dt)
        if view == "compact":
            records = [self._to_compact_record(r) for r in records]
        else:
            labels = self._load_label_map(start_dt=start_dt, end_dt=end_dt)
            if labels:
                for row in records:
                    key = (str(row.get("data_timestamp", "")), int(row.get("l0_version", 0)))
                    label_row = labels.get(key)
                    if label_row:
                        row.update(label_row)
        if fields:
            projected = self._project_fields(records, view=view, fields=fields)
            if isinstance(projected, dict):
                return projected
            records = projected
        records = self._apply_interval(records, interval=interval)
        return records

    def _project_fields(
        self,
        records: list[dict[str, Any]],
        *,
        view: str,
        fields: list[str],
    ) -> list[dict[str, Any]] | dict[str, Any]:
        requested = [f.strip() for f in fields if f and f.strip()]
        if not requested:
            return records
        if len(requested) > self._max_fields_per_query:
            return {"error": f"too many fields requested: {len(requested)} > {self._max_fields_per_query}"}

        if view == "compact":
            allowed = _COMPACT_FIELDS
        else:
            allowed = _FEATURE_BASE_FIELDS | _LABEL_FIELDS
        unknown = [f for f in requested if f not in allowed]
        if unknown:
            return {"error": f"unknown fields: {','.join(sorted(unknown))}"}

        return [{k: row.get(k) for k in requested} for row in records]

    def _apply_interval(self, records: list[dict[str, Any]], *, interval: str) -> list[dict[str, Any]]:
        step = _VALID_INTERVALS[interval]
        if step <= 1 or not records:
            return records

        out: list[dict[str, Any]] = []
        last_bucket: int | None = None
        last_direction: str | None = None
        for row in sorted(records, key=lambda r: str(r.get("data_timestamp", ""))):
            ts = self._coerce_timestamp(row.get("data_timestamp"))
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

    def _load_feature_range(self, *, start_dt: datetime, end_dt: datetime) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for date_str in self._iter_trade_dates(start_dt, end_dt):
            path = self._feature_dir / f"feature_{date_str}.parquet"
            if not path.exists():
                continue
            try:
                rows.extend(pq.read_table(path).to_pylist())
            except Exception as exc:
                logger.error("[ResearchFeatureStore] feature read failed path=%s error=%s", path.name, exc)
        return [
            r for r in rows
            if self._in_range(self._coerce_timestamp(r.get("data_timestamp")), start_dt, end_dt)
        ]

    def _load_label_map(self, *, start_dt: datetime, end_dt: datetime) -> dict[tuple[str, int], dict[str, Any]]:
        out: dict[tuple[str, int], dict[str, Any]] = {}
        for date_str in self._iter_trade_dates(start_dt, end_dt):
            path = self._label_dir / f"label_{date_str}.parquet"
            if not path.exists():
                continue
            try:
                rows = pq.read_table(path).to_pylist()
            except Exception as exc:
                logger.error("[ResearchFeatureStore] label read failed path=%s error=%s", path.name, exc)
                continue
            for row in rows:
                ts = self._coerce_timestamp(row.get("data_timestamp"))
                if not self._in_range(ts, start_dt, end_dt):
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

    def _load_latest_feature(self, *, count: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        files = sorted(self._feature_dir.glob("feature_*.parquet"), reverse=True)
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

    def _append_rows(self, tier_dir: Path, tier_name: str, date_str: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        table_new = pa.Table.from_pylist(rows)
        path = tier_dir / f"{tier_name}_{date_str}.parquet"
        try:
            if path.exists():
                table_old = pq.read_table(path)
                table = pa.concat_tables([table_old, table_new], promote_options="none")
            else:
                table = table_new
            pq.write_table(table, path, compression="zstd", use_dictionary=True)
        except Exception as exc:
            logger.error(
                "[ResearchFeatureStore] append failed tier=%s date=%s error=%s",
                tier_name,
                date_str,
                exc,
            )

    def _update_pending_labels(self, *, ts: datetime, spot: float, symbol: str, version: int) -> None:
        done: list[tuple[str, int, str]] = []
        to_append: list[dict[str, Any]] = []
        for key, state in list(self._pending_labels.items()):
            elapsed = max(0.0, (ts - state.ts).total_seconds())
            current_ret = (spot / state.base_spot) - 1.0 if state.base_spot > 0 else 0.0
            state.min_ret = min(state.min_ret, current_ret)
            state.max_ret = max(state.max_ret, current_ret)
            if state.last_spot > 0 and spot > 0:
                state.log_returns.append(math.log(spot / state.last_spot))
            state.last_spot = spot

            for horizon, sec in self._horizons.items():
                if state.fwd_ret[horizon] is None and elapsed >= sec:
                    state.fwd_ret[horizon] = current_ret

            if elapsed >= self._max_horizon_seconds:
                rv = self._f32(self._safe_std(state.log_returns))
                label_row = {
                    "data_timestamp": state.ts.isoformat(),
                    "l0_version": state.l0_version,
                    "symbol": state.symbol,
                    "fwd_ret_1m": self._f32(state.fwd_ret["1m"]),
                    "fwd_ret_5m": self._f32(state.fwd_ret["5m"]),
                    "fwd_ret_15m": self._f32(state.fwd_ret["15m"]),
                    "fwd_ret_60m": self._f32(state.fwd_ret["60m"]),
                    "max_adverse_excursion": self._f32(state.min_ret),
                    "realized_vol_horizon": rv,
                    "horizon_observed_seconds": self._f32(elapsed),
                    "stored_at": datetime.now(_UTC).isoformat(),
                }
                to_append.append(label_row)
                done.append(key)

        for key in done:
            self._pending_labels.pop(key, None)

        if to_append:
            date_str = ts.astimezone(_ET).strftime("%Y%m%d")
            self._append_rows(self._label_dir, "label", date_str, to_append)

    def _cleanup_retention_if_needed(self, date_str: str) -> None:
        if self._last_cleanup_date == date_str:
            return
        self._last_cleanup_date = date_str
        now_et = datetime.now(_ET).date()
        self._cleanup_tier(self._raw_dir, "raw", now_et, self._raw_retention_days)
        self._cleanup_tier(self._feature_dir, "feature", now_et, self._feature_retention_days)
        self._cleanup_tier(self._label_dir, "label", now_et, self._label_retention_days)

    def _cleanup_tier(self, tier_dir: Path, prefix: str, now_et_date: Any, retention_days: int) -> None:
        cutoff = now_et_date - timedelta(days=max(1, retention_days))
        for path in tier_dir.glob(f"{prefix}_*.parquet"):
            name = path.stem
            date_part = name.split("_")[-1]
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

    @staticmethod
    def _to_compact_record(row: dict[str, Any]) -> dict[str, Any]:
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

    @staticmethod
    def _records_to_parquet(records: list[dict[str, Any]]) -> bytes:
        table = pa.Table.from_pylist(records)
        sink = pa.BufferOutputStream()
        pq.write_table(table, sink, compression="zstd", use_dictionary=True)
        return sink.getvalue().to_pybytes()

    @staticmethod
    def _iter_trade_dates(start_dt: datetime, end_dt: datetime) -> list[str]:
        cur = start_dt.astimezone(_ET).date()
        end = end_dt.astimezone(_ET).date()
        out: list[str] = []
        while cur <= end:
            out.append(cur.strftime("%Y%m%d"))
            cur += timedelta(days=1)
        return out

    @staticmethod
    def _extract_as_of_utc(snapshot: Any, payload: Any, ts: datetime) -> str:
        extra = getattr(snapshot, "extra_metadata", None)
        if isinstance(extra, dict):
            raw = extra.get("source_data_timestamp_utc")
            dt = ResearchFeatureStore._coerce_timestamp(raw)
            if dt is not None:
                return dt.isoformat()
        dt2 = ResearchFeatureStore._coerce_timestamp(getattr(payload, "data_timestamp", None))
        if dt2 is not None:
            return dt2.isoformat()
        return ts.isoformat()

    @staticmethod
    def _in_range(ts: datetime | None, start_dt: datetime, end_dt: datetime) -> bool:
        if ts is None:
            return False
        return start_dt <= ts <= end_dt

    @staticmethod
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

    @staticmethod
    def _coerce_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _to_float(value: Any, default: float | None = None) -> float | None:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return default
        if not math.isfinite(num):
            return default
        return num

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_std(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean_v = sum(values) / len(values)
        var = sum((x - mean_v) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(max(var, 0.0))

    @staticmethod
    def _f32(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

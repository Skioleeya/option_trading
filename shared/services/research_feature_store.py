"""Research feature store for strategy R&D and parameter tuning."""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from shared.config import settings
from shared.services.research_feature_store_io import (
    cleanup_retention_if_needed,
    enqueue_export,
    load_latest_feature,
    project_fields,
    query_records,
    records_to_parquet,
    to_compact_record,
)
from shared.services.research_feature_store_schema import (
    _PendingOutcome,
    _VALID_FORMATS,
    _VALID_INTERVALS,
    _VALID_VIEWS,
    tier_schema,
)
from shared.services.research_feature_store_utils import (
    _ET,
    _UTC,
    coerce_dict,
    coerce_int,
    coerce_timestamp,
    extract_as_of_utc,
    f32,
    safe_std,
    to_float,
)
from shared.system.tactical_triad_logic import compute_vrp

logger = logging.getLogger(__name__)


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
        for path in (self._raw_dir, self._feature_dir, self._label_dir, self._export_dir):
            path.mkdir(parents=True, exist_ok=True)

        self._raw_retention_days = int(raw_retention_days or settings.research_raw_retention_days)
        self._feature_retention_days = int(
            feature_retention_days or settings.research_feature_retention_days
        )
        self._label_retention_days = int(label_retention_days or settings.research_label_retention_days)
        self._max_fields_per_query = int(settings.history_max_fields_per_query)
        self._max_points_per_query = int(settings.history_max_points_per_query)

        self._pending_labels: dict[tuple[str, int, str], _PendingOutcome] = {}
        self._jobs: dict[str, dict[str, Any]] = {}
        self._last_cleanup_date: str | None = None
        self._last_sample_bucket_5s: int | None = None
        self._last_direction: str | None = None
        self._last_net_gex: float | None = None
        self._horizons = {"1m": 60.0, "5m": 300.0, "15m": 900.0, "60m": 3600.0}
        self._max_horizon_seconds = max(self._horizons.values())

    def append_tick(self, *, decision: Any, snapshot: Any, payload: Any) -> None:
        """Append current tick to raw/feature tables and update outcome labels."""
        ts = coerce_timestamp(getattr(payload, "data_timestamp", None)) or datetime.now(_UTC)
        spot = to_float(getattr(snapshot, "spot", getattr(payload, "spot", None)))
        if spot is None or spot <= 0.0:
            return

        symbol = "SPY"
        l0_version = coerce_int(getattr(snapshot, "version", getattr(payload, "version", 0)), 0)
        as_of_utc = extract_as_of_utc(snapshot, payload, ts)
        store_date = ts.astimezone(_ET).strftime("%Y%m%d")

        cleanup_retention_if_needed(self, store_date)
        self._update_pending_labels(ts=ts, spot=spot, symbol=symbol, version=l0_version)
        self._pending_labels.setdefault(
            (ts.isoformat(), l0_version, symbol),
            _PendingOutcome(ts=ts, l0_version=l0_version, symbol=symbol, base_spot=spot, last_spot=spot),
        )

        aggregates = getattr(snapshot, "aggregates", None)
        micro = getattr(snapshot, "microstructure", None)
        net_vanna_raw_sum = to_float(
            getattr(aggregates, "net_vanna_raw_sum", getattr(aggregates, "net_vanna", None)),
            0.0,
        )
        net_charm_raw_sum = to_float(
            getattr(aggregates, "net_charm_raw_sum", getattr(aggregates, "net_charm", None)),
            0.0,
        )

        direction = str(getattr(decision, "direction", "NEUTRAL"))
        guard_actions = list(getattr(decision, "guard_actions", []))
        net_gex = to_float(getattr(aggregates, "net_gex", None), 0.0)
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

        mtf = coerce_dict(getattr(micro, "mtf_consensus", None))
        raw_row = {
            "data_timestamp": ts.isoformat(),
            "as_of_utc": as_of_utc,
            "l0_version": l0_version,
            "symbol": symbol,
            "spot": f32(spot),
            "atm_iv": f32(to_float(getattr(aggregates, "atm_iv", None), 0.0)),
            "net_gex": f32(net_gex),
            "net_vanna_raw_sum": f32(net_vanna_raw_sum),
            "net_vanna": f32(net_vanna_raw_sum),
            "net_charm_raw_sum": f32(net_charm_raw_sum),
            "net_charm": f32(net_charm_raw_sum),
            "call_wall": f32(to_float(getattr(aggregates, "call_wall", None), 0.0)),
            "put_wall": f32(to_float(getattr(aggregates, "put_wall", None), 0.0)),
            "flip_level": f32(to_float(getattr(aggregates, "flip_level", None), 0.0)),
            "vpin_1m": f32(to_float(getattr(micro, "vpin_1m", None), 0.0)),
            "vpin_5m": f32(to_float(getattr(micro, "vpin_5m", None), 0.0)),
            "vpin_15m": f32(to_float(getattr(micro, "vpin_15m", None), 0.0)),
            "vpin_composite": f32(to_float(getattr(micro, "vpin_composite", None), 0.0)),
            "bbo_imbalance_raw": f32(to_float(getattr(micro, "bbo_imbalance_raw", None), 0.0)),
            "bbo_ewma_fast": f32(to_float(getattr(micro, "bbo_ewma_fast", None), 0.0)),
            "bbo_ewma_slow": f32(to_float(getattr(micro, "bbo_ewma_slow", None), 0.0)),
            "bbo_persistence": f32(to_float(getattr(micro, "bbo_persistence", None), 0.0)),
            "vol_accel_ratio": f32(to_float(getattr(micro, "vol_accel_ratio", None), 0.0)),
            "vol_accel_threshold": f32(to_float(getattr(micro, "vol_accel_threshold", None), 0.0)),
            "vol_accel_elevated": bool(getattr(micro, "vol_accel_elevated", False)),
            "vol_entropy": f32(to_float(getattr(micro, "vol_entropy", None), 0.0)),
            "session_phase": str(getattr(micro, "session_phase", "")),
            "mtf_consensus": str(mtf.get("consensus", "NEUTRAL")),
            "mtf_alignment": f32(to_float(mtf.get("alignment"), 0.0)),
            "mtf_strength": f32(to_float(mtf.get("strength"), 0.0)),
            "stored_at": datetime.now(_UTC).isoformat(),
        }

        longport_cols = self._longport_option_columns(snapshot)
        official_hv_decimal = to_float(longport_cols.get("longport_official_hv_decimal"), None)
        atm_iv_value = to_float(raw_row.get("atm_iv"), None)
        vrp_official_hv_based: float | None = None
        if official_hv_decimal is not None and atm_iv_value is not None and atm_iv_value > 0.0:
            vrp_official_hv_based = f32(compute_vrp(atm_iv_value, official_hv_decimal))

        feature_row = {
            **raw_row,
            "skew_25d_normalized": self._feature_value(decision, "skew_25d_normalized"),
            "rr25_call_minus_put": self._feature_value(decision, "rr25_call_minus_put"),
            "realized_volatility_15m": self._feature_value(decision, "realized_volatility_15m"),
            "vol_risk_premium": self._feature_value(decision, "vol_risk_premium"),
            "vrp_realized_based": self._feature_value(decision, "vrp_realized_based"),
            **longport_cols,
            "vrp_official_hv_based": vrp_official_hv_based,
            "direction": direction,
            "confidence": f32(to_float(getattr(decision, "confidence", None), 0.0)),
            "pre_guard_direction": str(getattr(decision, "pre_guard_direction", "NEUTRAL")),
            "guard_actions_json": json.dumps(guard_actions, ensure_ascii=True),
            "fusion_weights_json": json.dumps(coerce_dict(getattr(decision, "fusion_weights", {})), ensure_ascii=True),
            "signal_summary_json": json.dumps(coerce_dict(getattr(decision, "signal_summary", {})), ensure_ascii=True),
            "feature_vector_json": json.dumps(coerce_dict(getattr(decision, "feature_vector", {})), ensure_ascii=True),
            "iv_regime": str(getattr(decision, "iv_regime", "NORMAL") or "NORMAL"),
            "gex_intensity": str(getattr(decision, "gex_intensity", "NEUTRAL") or "NEUTRAL"),
            "max_impact": f32(to_float(getattr(decision, "max_impact", None), 0.0)),
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

        start_dt = coerce_timestamp(start)
        end_dt = coerce_timestamp(end)
        if start_dt is None or end_dt is None:
            return {"error": "invalid start/end timestamp"}
        if end_dt < start_dt:
            return {"error": "end must be >= start"}
        if view_norm == "audit":
            return {"error": "audit view is served by /history endpoint"}

        records = query_records(
            self,
            start_dt=start_dt,
            end_dt=end_dt,
            view=view_norm,
            fields=fields,
            interval=interval_norm,
        )
        if isinstance(records, dict):
            return records
        if len(records) > self._max_points_per_query:
            job_id = enqueue_export(self, records=records, fmt=fmt_norm)
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
                "bytes": records_to_parquet(records),
            }
        return {"status": "ok", "count": len(records), "format": "jsonl", "records": records}

    async def get_export_job(self, job_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        return dict(job) if job else None

    async def read_export(self, job_id: str) -> tuple[str, bytes] | None:
        job = self._jobs.get(job_id)
        if not job or job.get("status") != "done":
            return None
        path = Path(job["path"])
        if not path.exists():
            return None
        content_type = "application/x-parquet" if path.suffix == ".parquet" else "application/x-ndjson"
        return content_type, path.read_bytes()

    def latest_feature_view(
        self,
        *,
        count: int,
        view: str,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        records = load_latest_feature(self, count=max(count * 4, 256))
        if view == "compact":
            records = [to_compact_record(r) for r in records]
        if fields:
            projected = project_fields(self, records, view=view, fields=fields)
            if isinstance(projected, dict):
                return []
            records = projected
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

    def _feature_value(self, decision: Any, key: str) -> float | None:
        features = getattr(decision, "feature_vector", {})
        if not isinstance(features, dict):
            return None
        return f32(to_float(features.get(key), None))

    def _longport_option_columns(self, snapshot: Any) -> dict[str, float | int | None]:
        extra = getattr(snapshot, "extra_metadata", None)
        diagnostics = extra.get("longport_option_diagnostics", {}) if isinstance(extra, dict) else {}
        diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
        return {
            "longport_tier2_contracts": coerce_int(diagnostics.get("tier2_contracts"), 0),
            "longport_tier3_contracts": coerce_int(diagnostics.get("tier3_contracts"), 0),
            "longport_tier2_standard_ratio": f32(to_float(diagnostics.get("tier2_standard_ratio"), 0.0)),
            "longport_tier3_standard_ratio": f32(to_float(diagnostics.get("tier3_standard_ratio"), 0.0)),
            "longport_tier2_avg_premium": f32(to_float(diagnostics.get("tier2_avg_premium"), 0.0)),
            "longport_tier3_avg_premium": f32(to_float(diagnostics.get("tier3_avg_premium"), 0.0)),
            "longport_official_hv_decimal": f32(to_float(diagnostics.get("official_hv_decimal"), None)),
            "longport_official_hv_sample_count": coerce_int(diagnostics.get("official_hv_sample_count"), 0),
            "longport_official_hv_age_sec": f32(to_float(diagnostics.get("official_hv_age_sec"), None)),
        }

    def _append_rows(self, tier_dir: Path, tier_name: str, date_str: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        schema = tier_schema(tier_name)
        path = tier_dir / f"{tier_name}_{date_str}.parquet"
        try:
            table_new = pa.Table.from_pylist(rows, schema=schema)
            table = table_new
            if path.exists():
                table_old = pq.read_table(path, schema=schema)
                table = pa.concat_tables([table_old, table_new], promote_options="none")
            pq.write_table(table, path, compression="zstd", use_dictionary=True)
        except Exception as exc:
            logger.error("[ResearchFeatureStore] append failed tier=%s date=%s error=%s", tier_name, date_str, exc)

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
                to_append.append(
                    {
                        "data_timestamp": state.ts.isoformat(),
                        "l0_version": state.l0_version,
                        "symbol": state.symbol,
                        "fwd_ret_1m": f32(state.fwd_ret["1m"]),
                        "fwd_ret_5m": f32(state.fwd_ret["5m"]),
                        "fwd_ret_15m": f32(state.fwd_ret["15m"]),
                        "fwd_ret_60m": f32(state.fwd_ret["60m"]),
                        "max_adverse_excursion": f32(state.min_ret),
                        "realized_vol_horizon": f32(safe_std(state.log_returns)),
                        "horizon_observed_seconds": f32(elapsed),
                        "stored_at": datetime.now(_UTC).isoformat(),
                    }
                )
                done.append(key)

        for key in done:
            self._pending_labels.pop(key, None)
        if to_append:
            label_date = ts.astimezone(_ET).strftime("%Y%m%d")
            self._append_rows(self._label_dir, "label", label_date, to_append)

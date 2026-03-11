#!/usr/bin/env python3
"""
EOD cold-storage bucketing with manifest indexing.

Reads per-day cold storage files, computes day metrics, classifies day type,
and writes:
  - daily manifest
  - by-regime manifest (primary tag only, index-only)
  - quality report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import pstdev
from typing import Any

import pyarrow.parquet as pq
from zoneinfo import ZoneInfo


DEFAULT_CONFIG = Path("scripts/diagnostics/config/eod_bucket_thresholds.json")
DEFAULT_ROOT = Path("data")
DEFAULT_OUT_ROOT = Path("data/cold")
VERSION = "v2"


@dataclass(frozen=True)
class SourceEntry:
    role: str
    path: Path
    required: bool


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _today_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_iso_z(raw: Any) -> str:
    if isinstance(raw, datetime):
        dt = raw
    else:
        text = str(raw or "").strip()
        if not text:
            return ""
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _to_et_dt(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(ZoneInfo("America/New_York"))


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(n):
        return None
    return n


def _sign(v: float) -> int:
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def _collect_sources(root: Path, date_str: str) -> list[SourceEntry]:
    return [
        SourceEntry("research_raw", root / "research" / "raw" / f"raw_{date_str}.parquet", True),
        SourceEntry("research_feature", root / "research" / "feature" / f"feature_{date_str}.parquet", True),
        SourceEntry("research_label", root / "research" / "label" / f"label_{date_str}.parquet", True),
        SourceEntry("atm_series", root / "atm_decay" / f"atm_series_{date_str}.jsonl", False),
        SourceEntry("mtf_iv_series", root / "mtf_iv" / f"mtf_iv_series_{date_str}.jsonl", False),
        SourceEntry("wall_series", root / "wall_migration" / f"wall_series_{date_str}.jsonl", False),
    ]


def _read_rows(path: Path) -> int:
    return pq.read_table(path).num_rows


def _find_prev_close_spot(root: Path, date_str: str) -> tuple[float | None, str | None]:
    raw_dir = root / "research" / "raw"
    if not raw_dir.exists():
        return None, None
    candidates: list[str] = []
    for path in raw_dir.glob("raw_*.parquet"):
        name = path.name
        if len(name) != len("raw_YYYYMMDD.parquet"):
            continue
        day = name[4:12]
        if day < date_str:
            candidates.append(day)
    if not candidates:
        return None, None
    prev_day = sorted(candidates)[-1]
    prev_path = raw_dir / f"raw_{prev_day}.parquet"
    try:
        table = pq.read_table(prev_path, columns=["spot"])
    except Exception:
        return None, prev_day
    spots = table.column("spot").to_pylist()
    for i in range(len(spots) - 1, -1, -1):
        val = _to_float(spots[i])
        if val is not None:
            return val, prev_day
    return None, prev_day


def _extract_key_level(flip: float | None, call_wall: float | None, put_wall: float | None) -> float | None:
    if flip is not None:
        return flip
    if call_wall is not None and put_wall is not None:
        return (call_wall + put_wall) / 2.0
    return None


def _parse_open_window(text: str) -> tuple[int, int, int, int]:
    start_h, start_m, end_h, end_m = 9, 30, 10, 0
    try:
        start_txt, end_txt = text.split("-", 1)
        start_h, start_m = [int(x) for x in start_txt.split(":", 1)]
        end_h, end_m = [int(x) for x in end_txt.split(":", 1)]
    except (TypeError, ValueError):
        pass
    return start_h, start_m, end_h, end_m


def _read_raw_metrics(raw_path: Path, cfg_thresholds: dict[str, Any], prev_close_spot: float | None) -> dict[str, Any]:
    table = pq.read_table(raw_path)
    rows = table.num_rows
    if rows <= 1:
        return {
            "rows": rows,
            "net_return": 0.0,
            "realized_range": 0.0,
            "open_rv_1m": 0.0,
            "ofi_persistence": 0.0,
            "max_abs_jump": 0.0,
            "state_switch_rate": 0.0,
            "intraday_followthrough": 0.0,
            "overnight_gap": 0.0,
            "overnight_gap_available": False,
            "atm_iv_change_pct": 0.0,
            "atm_iv_available": False,
            "pin_band_ratio": 0.0,
            "close_to_key_level": 1.0,
            "key_level_coverage": 0.0,
            "start_timestamp": "",
            "end_timestamp": "",
        }

    cols: dict[str, list[Any]] = {}
    for name in (
        "data_timestamp",
        "spot",
        "atm_iv",
        "ofi_norm",
        "bbo_imbalance_raw",
        "flip_level",
        "call_wall",
        "put_wall",
    ):
        if name in table.column_names:
            cols[name] = table.column(name).to_pylist()
        else:
            cols[name] = [None] * rows

    spots: list[float] = []
    ts_vals: list[datetime] = []
    ofi_vals: list[float] = []
    iv_vals: list[float | None] = []
    key_levels: list[float | None] = []
    ofi_source = "ofi_norm" if "ofi_norm" in table.column_names else (
        "bbo_imbalance_raw" if "bbo_imbalance_raw" in table.column_names else "missing"
    )

    for idx in range(rows):
        spot = _to_float(cols["spot"][idx])
        ts = _to_et_dt(cols["data_timestamp"][idx])
        if spot is None or ts is None:
            continue
        if ofi_source == "ofi_norm":
            ofi = _to_float(cols["ofi_norm"][idx])
        elif ofi_source == "bbo_imbalance_raw":
            ofi = _to_float(cols["bbo_imbalance_raw"][idx])
        else:
            ofi = None
        iv = _to_float(cols["atm_iv"][idx])
        flip = _to_float(cols["flip_level"][idx])
        call_wall = _to_float(cols["call_wall"][idx])
        put_wall = _to_float(cols["put_wall"][idx])
        key = _extract_key_level(flip, call_wall, put_wall)

        spots.append(spot)
        ts_vals.append(ts)
        ofi_vals.append(ofi if ofi is not None else 0.0)
        iv_vals.append(iv)
        key_levels.append(key)

    if len(spots) <= 1:
        return {
            "rows": rows,
            "net_return": 0.0,
            "realized_range": 0.0,
            "open_rv_1m": 0.0,
            "ofi_persistence": 0.0,
            "max_abs_jump": 0.0,
            "state_switch_rate": 0.0,
            "intraday_followthrough": 0.0,
            "overnight_gap": 0.0,
            "overnight_gap_available": False,
            "atm_iv_change_pct": 0.0,
            "atm_iv_available": False,
            "pin_band_ratio": 0.0,
            "close_to_key_level": 1.0,
            "key_level_coverage": 0.0,
            "start_timestamp": "",
            "end_timestamp": "",
            "ofi_source": ofi_source,
        }

    open_price = spots[0]
    close_price = spots[-1]
    net_return = (close_price - open_price) / open_price if open_price else 0.0
    intraday_followthrough = net_return
    realized_range = (max(spots) - min(spots)) / open_price if open_price else 0.0

    step_returns: list[float] = []
    for i in range(1, len(spots)):
        prev = spots[i - 1]
        cur = spots[i]
        step_returns.append((cur - prev) / prev if prev else 0.0)
    max_abs_jump = max((abs(v) for v in step_returns), default=0.0)

    signed_changes = 0
    for i in range(1, len(step_returns)):
        if step_returns[i - 1] == 0 or step_returns[i] == 0:
            continue
        if step_returns[i - 1] * step_returns[i] < 0:
            signed_changes += 1
    state_switch_rate = signed_changes / max(1, len(step_returns) - 1)

    high_cfg = cfg_thresholds["high_vol_open"]
    start_h, start_m, end_h, end_m = _parse_open_window(str(high_cfg.get("window", "09:30-10:00")))
    open_window_returns: list[float] = []
    for i in range(1, len(spots)):
        ts = ts_vals[i]
        in_window = (
            (ts.hour > start_h or (ts.hour == start_h and ts.minute >= start_m))
            and (ts.hour < end_h or (ts.hour == end_h and ts.minute <= end_m))
        )
        if in_window:
            open_window_returns.append(step_returns[i - 1])
    open_rv_1m = pstdev(open_window_returns) if len(open_window_returns) >= 2 else 0.0

    direction = _sign(net_return)
    aligned = 0
    considered = 0
    if direction != 0:
        for val in ofi_vals:
            if val == 0:
                continue
            considered += 1
            if _sign(val) == direction:
                aligned += 1
    ofi_persistence = (aligned / considered) if considered else 0.0

    finite_ivs = [v for v in iv_vals if v is not None and v > 0]
    atm_iv_available = len(finite_ivs) >= 2
    if atm_iv_available:
        first_iv = finite_ivs[0]
        last_iv = finite_ivs[-1]
        atm_iv_change_pct = (last_iv - first_iv) / first_iv
    else:
        atm_iv_change_pct = 0.0

    pin_width = float(cfg_thresholds["pinning_day"]["pin_band_width"])
    key_eligible = 0
    key_inside = 0
    close_key: float | None = None
    for i, key in enumerate(key_levels):
        if key is None:
            continue
        key_eligible += 1
        rel = abs(spots[i] - key) / spots[i] if spots[i] else 1.0
        if rel <= pin_width:
            key_inside += 1
    for i in range(len(key_levels) - 1, -1, -1):
        if key_levels[i] is not None:
            close_key = key_levels[i]
            break
    pin_band_ratio = key_inside / key_eligible if key_eligible else 0.0
    key_level_coverage = key_eligible / len(spots)
    close_to_key_level = (
        abs(close_price - close_key) / close_price if (close_key is not None and close_price) else 1.0
    )

    overnight_gap_available = prev_close_spot is not None and prev_close_spot != 0
    overnight_gap = ((open_price - prev_close_spot) / prev_close_spot) if overnight_gap_available else 0.0

    return {
        "rows": rows,
        "net_return": net_return,
        "intraday_followthrough": intraday_followthrough,
        "overnight_gap": overnight_gap,
        "overnight_gap_available": overnight_gap_available,
        "realized_range": realized_range,
        "open_rv_1m": open_rv_1m,
        "ofi_persistence": ofi_persistence,
        "max_abs_jump": max_abs_jump,
        "state_switch_rate": state_switch_rate,
        "atm_iv_change_pct": atm_iv_change_pct,
        "atm_iv_available": atm_iv_available,
        "pin_band_ratio": pin_band_ratio,
        "close_to_key_level": close_to_key_level,
        "key_level_coverage": key_level_coverage,
        "start_timestamp": _to_iso_z(ts_vals[0]),
        "end_timestamp": _to_iso_z(ts_vals[-1]),
        "ofi_source": ofi_source,
    }


def _key_null_pct(path: Path, keys: list[str]) -> dict[str, float | str]:
    table = pq.read_table(path)
    result: dict[str, float | str] = {}
    for k in keys:
        if k not in table.column_names:
            result[k] = "missing"
            continue
        arr = table[k]
        result[k] = arr.null_count / max(1, table.num_rows)
    return result


def _classify_metrics(
    metrics: dict[str, Any], thresholds: dict[str, Any], primary_priority: list[str]
) -> tuple[list[str], str, list[str]]:
    matched: list[str] = []
    hits: list[str] = []

    high = thresholds["high_vol_open"]
    if metrics["open_rv_1m"] >= float(high["open_rv_1m_threshold"]):
        matched.append("high_vol_open")
        hits.append("high_vol_open: open_rv_1m >= threshold")

    trend = thresholds["trend_day"]
    if (
        abs(metrics["net_return"]) >= float(trend["abs_ret_threshold"])
        and metrics["ofi_persistence"] >= float(trend["ofi_persistence_threshold"])
    ):
        matched.append("trend_day")
        hits.append("trend_day: abs_ret and ofi_persistence passed")

    rg = thresholds["range_day"]
    if (
        metrics["realized_range"] >= float(rg["realized_range_threshold"])
        and abs(metrics["net_return"]) <= float(rg["net_return_cap"])
    ):
        matched.append("range_day")
        hits.append("range_day: realized_range high with capped net_return")

    gap = thresholds["gap_trend_day"]
    if metrics["overnight_gap_available"]:
        cond = (
            abs(metrics["overnight_gap"]) >= float(gap["overnight_gap_abs_min"])
            and abs(metrics["intraday_followthrough"]) >= float(gap["intraday_followthrough_abs_min"])
        )
        if cond and bool(gap.get("require_same_direction", True)):
            cond = _sign(metrics["overnight_gap"]) != 0 and _sign(metrics["overnight_gap"]) == _sign(
                metrics["intraday_followthrough"]
            )
        if cond:
            matched.append("gap_trend_day")
            hits.append("gap_trend_day: overnight_gap and followthrough passed")

    crush = thresholds["vol_crush_day"]
    if (
        metrics["atm_iv_available"]
        and metrics["atm_iv_change_pct"] <= float(crush["atm_iv_change_pct_max"])
        and abs(metrics["net_return"]) <= float(crush["net_return_cap"])
        and metrics["realized_range"] <= float(crush["realized_range_cap"])
    ):
        matched.append("vol_crush_day")
        hits.append("vol_crush_day: iv crush with muted price action")

    pin = thresholds["pinning_day"]
    if (
        metrics["key_level_coverage"] > 0
        and metrics["close_to_key_level"] <= float(pin["close_to_key_level_max"])
        and metrics["pin_band_ratio"] >= float(pin["pin_band_ratio_min"])
        and metrics["realized_range"] <= float(pin["realized_range_cap"])
    ):
        matched.append("pinning_day")
        hits.append("pinning_day: spot clustered near key level")

    whipsaw = thresholds["whipsaw_day"]
    if (
        metrics["state_switch_rate"] >= float(whipsaw["state_switch_rate_min"])
        and metrics["realized_range"] >= float(whipsaw["realized_range_min"])
        and abs(metrics["net_return"]) <= float(whipsaw["net_return_cap"])
    ):
        matched.append("whipsaw_day")
        hits.append("whipsaw_day: high switching and high range with low drift")

    primary = "unclassified"
    for tag in primary_priority:
        if tag in matched:
            primary = tag
            break

    return matched, primary, hits


def run_archive(
    *,
    date_str: str,
    config_path: Path,
    root: Path,
    out_root: Path,
    strict_quality: bool,
) -> int:
    cfg = _load_json(config_path)
    thresholds = cfg["thresholds"]
    quality_gate = thresholds["quality_gate"]
    primary_priority = list(cfg["primary_priority"])
    classification_mode = str(cfg.get("classification_mode", "primary_only"))

    if classification_mode != "primary_only":
        raise ValueError("Only classification_mode=primary_only is supported in v2.")

    sources = _collect_sources(root=root, date_str=date_str)
    source_files: list[dict[str, Any]] = []
    quality_reasons: list[str] = []

    rows_by_role: dict[str, int] = {}
    required_missing = 0
    for src in sources:
        if not src.path.exists():
            if src.required:
                required_missing += 1
                quality_reasons.append(f"missing required source: {src.role}")
            continue
        size = src.path.stat().st_size
        source_files.append(
            {
                "role": src.role,
                "path": src.path.as_posix(),
                "size_bytes": size,
                "sha256": _sha256(src.path),
            }
        )
        if src.path.suffix == ".parquet":
            rows_by_role[src.role] = _read_rows(src.path)

    raw_path = root / "research" / "raw" / f"raw_{date_str}.parquet"
    key_null_pct: dict[str, float | str] = {}
    if raw_path.exists():
        prev_close_spot, prev_day = _find_prev_close_spot(root, date_str)
        raw_metrics = _read_raw_metrics(raw_path, thresholds, prev_close_spot)
        raw_metrics["prev_trade_day"] = prev_day or ""
        key_null_pct = _key_null_pct(raw_path, ["data_timestamp", "spot", "atm_iv", "net_gex"])
    else:
        raw_metrics = {
            "rows": 0,
            "net_return": 0.0,
            "intraday_followthrough": 0.0,
            "overnight_gap": 0.0,
            "overnight_gap_available": False,
            "realized_range": 0.0,
            "open_rv_1m": 0.0,
            "ofi_persistence": 0.0,
            "max_abs_jump": 0.0,
            "state_switch_rate": 0.0,
            "atm_iv_change_pct": 0.0,
            "atm_iv_available": False,
            "pin_band_ratio": 0.0,
            "close_to_key_level": 1.0,
            "key_level_coverage": 0.0,
            "start_timestamp": "",
            "end_timestamp": "",
            "ofi_source": "missing",
            "prev_trade_day": "",
        }

    q_raw = int(quality_gate["min_rows_raw"])
    q_feature = int(quality_gate["min_rows_feature"])
    q_label = int(quality_gate["min_rows_label"])
    if rows_by_role.get("research_raw", 0) < q_raw:
        quality_reasons.append(f"raw rows below minimum: {rows_by_role.get('research_raw', 0)} < {q_raw}")
    if rows_by_role.get("research_feature", 0) < q_feature:
        quality_reasons.append(
            f"feature rows below minimum: {rows_by_role.get('research_feature', 0)} < {q_feature}"
        )
    if rows_by_role.get("research_label", 0) < q_label:
        quality_reasons.append(f"label rows below minimum: {rows_by_role.get('research_label', 0)} < {q_label}")

    max_null_pct = float(quality_gate.get("max_null_pct", 0.05))
    for col, pct in key_null_pct.items():
        if pct == "missing":
            quality_reasons.append(f"raw key column missing: {col}")
            continue
        if float(pct) > max_null_pct:
            quality_reasons.append(f"raw key column null ratio too high: {col}={float(pct):.4f}")

    matched_tags, primary_tag, rule_hits = _classify_metrics(
        metrics=raw_metrics,
        thresholds=thresholds,
        primary_priority=primary_priority,
    )

    quality_status = "PASS"
    if required_missing > 0 or quality_reasons:
        quality_status = "LOW_QUALITY_DAY"

    manifest = {
        "version": VERSION,
        "classification_mode": classification_mode,
        "date": date_str,
        "primary_tag": primary_tag,
        "tags": [primary_tag],
        "matched_tags": matched_tags,
        "source_files": source_files,
        "metrics": {
            "rows": rows_by_role,
            "raw_day": raw_metrics,
            "source_count": len(source_files),
        },
        "quality": {
            "status": quality_status,
            "reasons": quality_reasons,
            "min_rows": {"raw": q_raw, "feature": q_feature, "label": q_label},
            "key_null_pct": key_null_pct,
        },
        "rule_hits": rule_hits,
        "generated_at_utc": _utc_iso(),
    }

    daily_manifest = out_root / "daily" / date_str / "manifest.json"
    quality_report = out_root / "reports" / f"{date_str}_quality.json"
    daily_manifest.parent.mkdir(parents=True, exist_ok=True)
    quality_report.parent.mkdir(parents=True, exist_ok=True)
    daily_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    quality_report.write_text(
        json.dumps(
            {
                "date": date_str,
                "classification_mode": classification_mode,
                "primary_tag": primary_tag,
                "matched_tags": matched_tags,
                "status": quality_status,
                "reasons": quality_reasons,
                "rows": rows_by_role,
                "raw_metrics": raw_metrics,
                "generated_at_utc": _utc_iso(),
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    by_regime_manifest = out_root / "by_regime" / primary_tag / date_str / "manifest.json"
    by_regime_manifest.parent.mkdir(parents=True, exist_ok=True)
    by_regime_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    print(
        f"[EODBucket] date={date_str} primary={primary_tag} matched={','.join(matched_tags) if matched_tags else 'none'} "
        f"quality={quality_status} sources={len(source_files)}"
    )
    print(f"[EODBucket] daily_manifest={daily_manifest.as_posix()}")
    print(f"[EODBucket] by_regime_manifest={by_regime_manifest.as_posix()}")
    print(f"[EODBucket] quality_report={quality_report.as_posix()}")

    if quality_status == "LOW_QUALITY_DAY" and strict_quality:
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="EOD cold-storage bucketing with manifest indexing.")
    p.add_argument("--date", default=_today_et(), help="Trade date in YYYYMMDD. Default=today ET.")
    p.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Threshold config JSON path.",
    )
    p.add_argument("--root", default=str(DEFAULT_ROOT), help="Cold storage root path (default: data).")
    p.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="Manifest output root (default: data/cold).")
    p.add_argument("--strict-quality", action="store_true", help="Return 2 when quality gate is LOW_QUALITY_DAY.")
    return p


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_archive(
            date_str=str(args.date),
            config_path=Path(args.config),
            root=Path(args.root),
            out_root=Path(args.out_root),
            strict_quality=bool(args.strict_quality),
        )
    except Exception as exc:
        print(f"[EODBucket][ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())

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
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import exchange_calendars as xc
import pyarrow.parquet as pq
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eod_bucket_metrics import key_null_pct, read_raw_metrics
from eod_bucket_publish import (
    cleanup_stage_root,
    make_stage_root,
    publish_stage_file,
    publish_stage_tree,
    stage_daily_dir,
    stage_regime_dir,
    stage_report_path,
    write_stage_text,
)
from eod_bucket_research_sources import project_research_sources_from_canonical, sha256_file
from eod_bucket_rules import classify_metrics

DEFAULT_CONFIG = Path("scripts/diagnostics/config/eod_bucket_thresholds.json")
DEFAULT_ROOT = Path("data")
DEFAULT_OUT_ROOT = Path("data/cold")
VERSION = "v3"
XNYS_CAL = xc.get_calendar("XNYS")


@dataclass(frozen=True)
class SourceEntry:
    role: str
    path: Path
    required: bool


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _today_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d")


def _parse_date_str(date_str: str) -> datetime:
    text = str(date_str or "").strip()
    if len(text) != 8 or not text.isdigit():
        raise ValueError(f"Invalid date '{date_str}': expected YYYYMMDD.")
    try:
        return datetime.strptime(text, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"Invalid date '{date_str}': expected YYYYMMDD.") from exc


def _ensure_xnys_session(date_str: str) -> str:
    dt = _parse_date_str(date_str)
    iso = dt.strftime("%Y-%m-%d")
    if not XNYS_CAL.is_session(iso):
        raise ValueError(f"Date '{date_str}' is not an XNYS trading session.")
    return dt.strftime("%Y%m%d")


def _previous_xnys_session(date_str: str) -> str:
    dt = _parse_date_str(date_str)
    return XNYS_CAL.previous_session(dt.strftime("%Y-%m-%d")).strftime("%Y%m%d")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return sha256_file(path)


def _collect_sources(root: Path, date_str: str) -> list[SourceEntry]:
    return [
        SourceEntry("research_canonical", root / "research" / "canonical" / f"day_{date_str}.parquet", True),
        SourceEntry("atm_series", root / "atm_decay" / f"atm_series_{date_str}.jsonl", False),
        SourceEntry("mtf_iv_series", root / "mtf_iv" / f"mtf_iv_series_{date_str}.jsonl", False),
        SourceEntry("wall_series", root / "wall_migration" / f"wall_series_{date_str}.jsonl", False),
    ]


def _read_rows(path: Path) -> int:
    return pq.read_table(path).num_rows


def _freeze_source_file(*, src: SourceEntry, frozen_root: Path) -> Path:
    frozen_dir = frozen_root / "sources" / src.role
    frozen_dir.mkdir(parents=True, exist_ok=True)
    frozen_path = frozen_dir / src.path.name
    shutil.copy2(src.path, frozen_path)
    return frozen_path


def _find_prev_close_spot(root: Path, date_str: str) -> tuple[float | None, str | None]:
    prev_day = _previous_xnys_session(date_str)
    prev_path = root / "research" / "canonical" / f"day_{prev_day}.parquet"
    if not prev_path.exists():
        return None, prev_day
    try:
        table = pq.read_table(prev_path, columns=["spot"])
    except Exception:
        return None, prev_day
    spots = table.column("spot").to_pylist()
    for idx in range(len(spots) - 1, -1, -1):
        try:
            val = float(spots[idx])
        except (TypeError, ValueError):
            continue
        if val == val:
            return val, prev_day
    return None, prev_day


def _empty_raw_metrics() -> dict[str, Any]:
    return {
        "rows": 0,
        "net_return": 0.0,
        "intraday_followthrough": 0.0,
        "overnight_gap": 0.0,
        "overnight_gap_available": False,
        "realized_range": 0.0,
        "open_rv_1m": 0.0,
        "ofi_persistence": 0.0,
        "ofi_nonzero_coverage": 0.0,
        "directional_efficiency": 0.0,
        "open_side_persistence": 0.0,
        "close_to_extreme": 1.0,
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
        "midday_return": 0.0,
        "afternoon_return": 0.0,
    }


def _classify_metrics(metrics: dict[str, Any], thresholds: dict[str, Any], primary_priority: list[str]) -> dict[str, Any]:
    return classify_metrics(metrics, thresholds, primary_priority)


def _assert_publish_targets_absent(targets: list[Path]) -> None:
    conflicts = [path.as_posix() for path in targets if path.exists()]
    if conflicts:
        joined = ", ".join(conflicts)
        raise FileExistsError(f"final publish target already exists: {joined}")


def run_archive(
    *,
    date_str: str,
    config_path: Path,
    root: Path,
    out_root: Path,
    strict_quality: bool,
) -> int:
    date_str = _ensure_xnys_session(date_str)
    cfg = _load_json(config_path)
    thresholds = cfg["thresholds"]
    quality_gate = thresholds["quality_gate"]
    primary_priority = list(cfg["primary_priority"])
    classification_mode = str(cfg.get("classification_mode", "primary_plus_context_v1"))
    final_daily_dir = out_root / "daily" / date_str
    final_report = out_root / "reports" / f"{date_str}_quality.json"

    if classification_mode != "primary_plus_context_v1":
        raise ValueError("Only classification_mode=primary_plus_context_v1 is supported.")

    stage_root = make_stage_root(out_root=out_root, date_str=date_str)
    source_files: list[dict[str, Any]] = []
    quality_reasons: list[str] = []
    rows_by_role: dict[str, int] = {}
    required_missing = 0

    try:
        staged_daily_dir = stage_daily_dir(stage_root=stage_root, date_str=date_str)
        raw_path: Path | None = None
        for src in _collect_sources(root=root, date_str=date_str):
            if not src.path.exists():
                if src.required:
                    required_missing += 1
                    quality_reasons.append(f"missing required source: {src.role}")
                continue
            if src.role == "research_canonical":
                projected_files, projected_rows, raw_path = project_research_sources_from_canonical(
                    canonical_path=src.path,
                    frozen_root=staged_daily_dir,
                    final_daily_dir=final_daily_dir,
                    date_str=date_str,
                )
                source_files.extend(projected_files)
                rows_by_role.update(projected_rows)
                continue
            frozen_path = _freeze_source_file(src=src, frozen_root=staged_daily_dir)
            source_files.append(
                {
                    "role": src.role,
                    "path": (final_daily_dir / "sources" / src.role / src.path.name).as_posix(),
                    "source_path": src.path.as_posix(),
                    "size_bytes": frozen_path.stat().st_size,
                    "sha256": _sha256(frozen_path),
                }
            )

        key_nulls: dict[str, float | str] = {}
        if raw_path is not None and raw_path.exists():
            prev_close_spot, prev_day = _find_prev_close_spot(root, date_str)
            raw_metrics = read_raw_metrics(raw_path, thresholds, prev_close_spot)
            raw_metrics["prev_trade_day"] = prev_day or ""
            key_nulls = key_null_pct(raw_path, ["data_timestamp", "spot", "atm_iv", "net_gex"])
        else:
            raw_metrics = _empty_raw_metrics()

        for role, key in (
            ("research_raw", "min_rows_raw"),
            ("research_feature", "min_rows_feature"),
            ("research_label", "min_rows_label"),
        ):
            minimum = int(quality_gate[key])
            if rows_by_role.get(role, 0) < minimum:
                short_role = role.replace("research_", "")
                quality_reasons.append(f"{short_role} rows below minimum: {rows_by_role.get(role, 0)} < {minimum}")

        max_null_pct = float(quality_gate.get("max_null_pct", 0.05))
        for col, pct in key_nulls.items():
            if pct == "missing":
                quality_reasons.append(f"raw key column missing: {col}")
            elif float(pct) > max_null_pct:
                quality_reasons.append(f"raw key column null ratio too high: {col}={float(pct):.4f}")

        quality_failed = required_missing > 0 or bool(quality_reasons)
        quality_status = "LOW_QUALITY_DAY" if quality_failed else "PASS"
        if quality_failed:
            primary_day_type = "INCOMPLETE_SOURCE"
            context_modifiers = []
            close_profile = "UNKNOWN"
            rule_hits = [f"classification_blocked:{reason}" for reason in quality_reasons] or ["classification_blocked:missing_required_source"]
        else:
            classification = _classify_metrics(raw_metrics, thresholds, primary_priority)
            primary_day_type = str(classification["primary_day_type"])
            context_modifiers = list(classification["context_modifiers"])
            close_profile = str(classification["close_profile"])
            rule_hits = list(classification["rule_hits"])

        manifest = {
            "version": VERSION,
            "classification_mode": classification_mode,
            "date": date_str,
            "primary_day_type": primary_day_type,
            "context_modifiers": context_modifiers,
            "close_profile": close_profile,
            "source_files": source_files,
            "metrics": {"rows": rows_by_role, "raw_day": raw_metrics, "source_count": len(source_files)},
            "quality": {
                "status": quality_status,
                "reasons": quality_reasons,
                "classification_blocked": quality_failed,
                "min_rows": {
                    "raw": int(quality_gate["min_rows_raw"]),
                    "feature": int(quality_gate["min_rows_feature"]),
                    "label": int(quality_gate["min_rows_label"]),
                },
                "key_null_pct": key_nulls,
            },
            "rule_hits": rule_hits,
            "generated_at_utc": _utc_iso(),
        }

        staged_report = stage_report_path(stage_root=stage_root, date_str=date_str)
        staged_regime_dir = stage_regime_dir(
            stage_root=stage_root,
            date_str=date_str,
            primary_day_type=primary_day_type,
        )
        manifest_payload = json.dumps(manifest, indent=2, ensure_ascii=True)
        quality_payload = json.dumps(
            {
                "date": date_str,
                "classification_mode": classification_mode,
                "primary_day_type": primary_day_type,
                "context_modifiers": context_modifiers,
                "close_profile": close_profile,
                "status": quality_status,
                "reasons": quality_reasons,
                "classification_blocked": quality_failed,
                "rows": rows_by_role,
                "raw_metrics": raw_metrics,
                "generated_at_utc": _utc_iso(),
            },
            indent=2,
            ensure_ascii=True,
        )
        write_stage_text(staged_daily_dir / "manifest.json", manifest_payload)
        write_stage_text(staged_regime_dir / "manifest.json", manifest_payload)
        write_stage_text(staged_report, quality_payload)

        final_regime_dir = out_root / "by_regime" / primary_day_type / date_str
        _assert_publish_targets_absent([final_daily_dir, final_regime_dir, final_report])
        publish_stage_tree(staged=staged_daily_dir, final=final_daily_dir)
        publish_stage_tree(staged=staged_regime_dir, final=final_regime_dir)
        publish_stage_file(staged=staged_report, final=final_report)

        print(
            f"[EODBucket] date={date_str} primary_day_type={primary_day_type} "
            f"modifiers={','.join(context_modifiers) if context_modifiers else 'none'} "
            f"close_profile={close_profile} "
            f"quality={quality_status} sources={len(source_files)}"
        )
        print(f"[EODBucket] daily_manifest={(final_daily_dir / 'manifest.json').as_posix()}")
        print(f"[EODBucket] by_regime_manifest={(final_regime_dir / 'manifest.json').as_posix()}")
        print(f"[EODBucket] quality_report={final_report.as_posix()}")

        return 2 if quality_status == "LOW_QUALITY_DAY" and strict_quality else 0
    finally:
        cleanup_stage_root(stage_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EOD cold-storage bucketing with manifest indexing.")
    parser.add_argument("--date", default=_today_et(), help="Trade date in YYYYMMDD. Default=today ET.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Threshold config JSON path.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Cold storage root path (default: data).")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="Manifest output root (default: data/cold).")
    parser.add_argument("--strict-quality", action="store_true", help="Return 2 when quality gate is LOW_QUALITY_DAY.")
    return parser


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

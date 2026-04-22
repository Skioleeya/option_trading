from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path
from statistics import pstdev
from typing import Any

import pyarrow.parquet as pq
from zoneinfo import ZoneInfo


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


def _parse_clock(text: str, default_hour: int, default_minute: int) -> tuple[int, int]:
    try:
        hour, minute = [int(x) for x in str(text).split(":", 1)]
        return hour, minute
    except (TypeError, ValueError):
        return default_hour, default_minute


def _default_raw_metrics(rows: int, ofi_source: str) -> dict[str, Any]:
    return {
        "rows": rows,
        "session_rows_used": 0,
        "spot_outlier_rows_dropped": 0,
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
        "ofi_source": ofi_source,
        "midday_return": 0.0,
        "afternoon_return": 0.0,
    }


def _is_rth(ts: datetime) -> bool:
    return (ts.hour > 9 or (ts.hour == 9 and ts.minute >= 30)) and (ts.hour < 16 or (ts.hour == 16 and ts.minute <= 0))


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    idx = max(0, min(len(sorted_values) - 1, int(round((len(sorted_values) - 1) * q))))
    return sorted_values[idx]


def _trim_outlier_rows(
    spots: list[float],
    ts_vals: list[datetime],
    ofi_vals: list[float],
    iv_vals: list[float | None],
    key_levels: list[float | None],
    *,
    trim_quantile: float,
) -> tuple[list[float], list[datetime], list[float], list[float | None], list[float | None], int]:
    if trim_quantile <= 0.0 or len(spots) < 5:
        return spots, ts_vals, ofi_vals, iv_vals, key_levels, 0

    ordered = sorted(spots)
    lower = _quantile(ordered, trim_quantile)
    upper = _quantile(ordered, 1.0 - trim_quantile)
    kept: list[int] = [idx for idx, spot in enumerate(spots) if lower <= spot <= upper]
    dropped = len(spots) - len(kept)
    if len(kept) <= 1 or dropped <= 0:
        return spots, ts_vals, ofi_vals, iv_vals, key_levels, 0

    return (
        [spots[idx] for idx in kept],
        [ts_vals[idx] for idx in kept],
        [ofi_vals[idx] for idx in kept],
        [iv_vals[idx] for idx in kept],
        [key_levels[idx] for idx in kept],
        dropped,
    )


def _compute_close_to_extreme(direction: int, close_price: float, low_price: float, high_price: float) -> float:
    span = high_price - low_price
    if span <= 0 or direction == 0:
        return 1.0
    if direction > 0:
        return max(0.0, min(1.0, (high_price - close_price) / span))
    return max(0.0, min(1.0, (close_price - low_price) / span))


def read_raw_metrics(raw_path: Path, cfg_thresholds: dict[str, Any], prev_close_spot: float | None) -> dict[str, Any]:
    table = pq.read_table(raw_path)
    rows = table.num_rows
    if rows <= 1:
        return _default_raw_metrics(rows, "missing")

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
        cols[name] = table.column(name).to_pylist() if name in table.column_names else [None] * rows

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
        if spot is None or ts is None or not _is_rth(ts):
            continue
        if ofi_source == "ofi_norm":
            ofi = _to_float(cols["ofi_norm"][idx])
        elif ofi_source == "bbo_imbalance_raw":
            ofi = _to_float(cols["bbo_imbalance_raw"][idx])
        else:
            ofi = None
        key = _extract_key_level(
            _to_float(cols["flip_level"][idx]),
            _to_float(cols["call_wall"][idx]),
            _to_float(cols["put_wall"][idx]),
        )
        spots.append(spot)
        ts_vals.append(ts)
        ofi_vals.append(ofi if ofi is not None else 0.0)
        iv_vals.append(_to_float(cols["atm_iv"][idx]))
        key_levels.append(key)

    if len(spots) <= 1:
        return _default_raw_metrics(rows, ofi_source)

    trim_quantile = float(cfg_thresholds.get("raw_sanitizer", {}).get("spot_trim_quantile", 0.001))
    spots, ts_vals, ofi_vals, iv_vals, key_levels, outlier_rows_dropped = _trim_outlier_rows(
        spots,
        ts_vals,
        ofi_vals,
        iv_vals,
        key_levels,
        trim_quantile=trim_quantile,
    )
    if len(spots) <= 1:
        return _default_raw_metrics(rows, ofi_source)

    open_price = spots[0]
    close_price = spots[-1]
    low_price = min(spots)
    high_price = max(spots)
    net_return = (close_price - open_price) / open_price if open_price else 0.0
    intraday_followthrough = net_return
    realized_range = (high_price - low_price) / open_price if open_price else 0.0
    directional_efficiency = abs(net_return) / realized_range if realized_range > 0 else 0.0

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
        if (
            (ts.hour > start_h or (ts.hour == start_h and ts.minute >= start_m))
            and (ts.hour < end_h or (ts.hour == end_h and ts.minute <= end_m))
        ):
            open_window_returns.append(step_returns[i - 1])
    open_rv_1m = pstdev(open_window_returns) if len(open_window_returns) >= 2 else 0.0

    reversal_cfg = cfg_thresholds.get("reversal_day", {})
    pivot_h, pivot_m = _parse_clock(reversal_cfg.get("midday_pivot_time", "12:00"), 12, 0)
    pivot_idx = next(
        (
            i
            for i, ts in enumerate(ts_vals)
            if ts.hour > pivot_h or (ts.hour == pivot_h and ts.minute >= pivot_m)
        ),
        max(1, len(spots) // 2),
    )
    pivot_price = spots[pivot_idx]
    midday_return = (pivot_price - open_price) / open_price if open_price else 0.0
    afternoon_return = (close_price - pivot_price) / pivot_price if pivot_price else 0.0

    direction = _sign(net_return)
    aligned = 0
    considered = 0
    open_side_hits = 0
    if direction != 0:
        for spot in spots:
            if (spot - open_price) * direction >= 0:
                open_side_hits += 1
        for val in ofi_vals:
            if val == 0:
                continue
            considered += 1
            if _sign(val) == direction:
                aligned += 1

    ofi_persistence = (aligned / considered) if considered else 0.0
    ofi_nonzero_coverage = considered / max(1, len(ofi_vals))
    open_side_persistence = open_side_hits / len(spots) if direction != 0 else 0.0
    close_to_extreme = _compute_close_to_extreme(direction, close_price, low_price, high_price)

    finite_ivs = [v for v in iv_vals if v is not None and v > 0]
    atm_iv_available = len(finite_ivs) >= 2
    atm_iv_change_pct = ((finite_ivs[-1] - finite_ivs[0]) / finite_ivs[0]) if atm_iv_available else 0.0

    pin_cfg = cfg_thresholds.get("pinning", cfg_thresholds.get("pinning_day", {"pin_band_width": 0.0020}))
    pin_width = float(pin_cfg["pin_band_width"])
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
        "session_rows_used": len(spots),
        "spot_outlier_rows_dropped": outlier_rows_dropped,
        "net_return": net_return,
        "intraday_followthrough": intraday_followthrough,
        "overnight_gap": overnight_gap,
        "overnight_gap_available": overnight_gap_available,
        "realized_range": realized_range,
        "open_rv_1m": open_rv_1m,
        "ofi_persistence": ofi_persistence,
        "ofi_nonzero_coverage": ofi_nonzero_coverage,
        "directional_efficiency": directional_efficiency,
        "open_side_persistence": open_side_persistence,
        "close_to_extreme": close_to_extreme,
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
        "midday_return": midday_return,
        "afternoon_return": afternoon_return,
    }


def key_null_pct(path: Path, keys: list[str]) -> dict[str, float | str]:
    table = pq.read_table(path)
    result: dict[str, float | str] = {}
    for key in keys:
        if key not in table.column_names:
            result[key] = "missing"
            continue
        arr = table[key]
        result[key] = arr.null_count / max(1, table.num_rows)
    return result

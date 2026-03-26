"""Support helpers for PayloadAssemblerV2."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from l3_assembly.events.active_options_contract import active_option_row_from_dict


def to_utc_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def normalize_volume_map(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}

    out: dict[str, float] = {}
    for strike, volume in raw.items():
        try:
            strike_f = float(strike)
            volume_f = float(volume)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(strike_f) or not math.isfinite(volume_f):
            continue
        if strike_f <= 0.0 or volume_f < 0.0:
            continue
        out[str(strike)] = volume_f
    return out


def extract_wall_dyn_payload(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}

    call_state = raw.get("call_wall_state")
    put_state = raw.get("put_wall_state")
    wall_context = raw.get("wall_context")
    if call_state is None and put_state is None:
        return {}

    payload = {
        "call_wall_state": str(call_state) if call_state is not None else "",
        "put_wall_state": str(put_state) if put_state is not None else "",
    }
    if isinstance(wall_context, dict) and wall_context:
        payload["wall_context"] = dict(wall_context)
    return payload


def convert_active_option(row: dict[str, Any]) -> Any:
    return active_option_row_from_dict(row)


class SnapshotData:
    """Mutable accumulator for extracted snapshot fields."""

    __slots__ = (
        "spot",
        "atm_iv",
        "flip_level",
        "flip_level_cumulative",
        "zero_gamma_level",
        "snapshot_time",
        "gex_regime",
        "vanna_state",
        "momentum",
        "vrp",
        "vrp_state",
        "net_charm",
        "svol_corr",
        "svol_state",
        "fused_signal_direction",
        "wall_dyn",
        "wall_migration_data",
        "per_strike_gex",
        "mtf_consensus",
        "skew_dynamics",
        "volume_map",
        "net_gex",
        "call_wall",
        "put_wall",
        "iv_velocity",
        "header_volatility",
        "rust_active",
        "shm_stats",
        "source_data_timestamp_utc",
    )

    def __init__(self) -> None:
        self.spot: float = 0.0
        self.atm_iv: float = 0.0
        self.flip_level: float = 0.0
        self.flip_level_cumulative: float = 0.0
        self.zero_gamma_level: float = 0.0
        self.snapshot_time: Any = None
        self.gex_regime: str = "NEUTRAL"
        self.vanna_state: str = "NORMAL"
        self.momentum: str = "NEUTRAL"
        self.vrp: float | None = None
        self.vrp_state: str | None = None
        self.net_charm: float | None = None
        self.svol_corr: float | None = None
        self.svol_state: str | None = None
        self.fused_signal_direction: str | None = None
        self.wall_dyn: dict[str, Any] = {}
        self.wall_migration_data: dict[str, Any] = {}
        self.per_strike_gex: list[Any] = []
        self.mtf_consensus: dict[str, Any] = {}
        self.skew_dynamics: dict[str, Any] = {}
        self.volume_map: dict[str, float] = {}
        self.net_gex: float = 0.0
        self.call_wall: float = 0.0
        self.put_wall: float = 0.0
        self.iv_velocity: dict[str, Any] | None = None
        self.header_volatility: dict[str, Any] | None = None
        self.rust_active: bool = False
        self.shm_stats: dict[str, Any] | None = None
        self.source_data_timestamp_utc: Any = None

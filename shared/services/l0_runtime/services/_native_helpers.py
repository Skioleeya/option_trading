"""Rust-backed native helpers for service-layer packages."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from shared.services.l0_runtime.native_loader import load_l0_rust

_PACKAGE_DIR = Path(__file__).resolve().parents[1] / "_native_generated"
_L0_RUST = load_l0_rust(
    candidates=[
        _PACKAGE_DIR / "wave11" / "l0_rust.pyd",
    ],
    module_suffix="l0_rust_wave11_services_native_support",
)


def clamp_subscription_cap_native(configured_cap: int) -> int:
    return int(_L0_RUST.l0_subscription_clamp_cap(int(configured_cap)))


def collect_targets_native(rows: list[Any], spot: float) -> dict[str, Any]:
    data = dict(_L0_RUST.l0_subscription_collect_targets(list(rows), float(spot)))
    data["targets"] = set(data.get("targets", []))
    data["symbol_to_strike"] = {
        str(symbol): float(strike)
        for symbol, strike in dict(data.get("symbol_to_strike", {})).items()
    }
    return data


def select_targets_native(
    rows: list[Any],
    *,
    chain_snapshot: list[dict[str, Any]],
    spot: float,
    first_source_seen_at_mono: float | None,
    now_mono: float,
    initial_steps: int,
    dynamic_after_sec: float,
    coverage: float,
    core_buffer_steps: int,
) -> dict[str, Any]:
    data = dict(
        _L0_RUST.l0_subscription_select_targets(
            list(rows),
            list(chain_snapshot),
            float(spot),
            first_source_seen_at_mono,
            float(now_mono),
            int(initial_steps),
            float(dynamic_after_sec),
            float(coverage),
            int(core_buffer_steps),
        )
    )
    for key in ("targets", "core_targets", "sentinel_targets"):
        data[key] = set(data.get(key, []))
    data["symbol_to_strike"] = {
        str(symbol): float(strike)
        for symbol, strike in dict(data.get("symbol_to_strike", {})).items()
    }
    data["priority_by_symbol"] = {
        str(symbol): int(priority)
        for symbol, priority in dict(data.get("priority_by_symbol", {})).items()
    }
    return data


def enforce_cap_native(
    *,
    target_symbols: set[str],
    mandatory_symbols: set[str],
    spot: float | None,
    subscription_cap: int,
    symbol_to_strike: dict[str, float],
    symbol_priority: dict[str, int] | None = None,
) -> dict[str, Any]:
    data = dict(
        _L0_RUST.l0_subscription_enforce_cap(
            sorted(target_symbols),
            sorted(mandatory_symbols),
            int(subscription_cap),
            dict(symbol_to_strike),
            spot,
            dict(symbol_priority or {}),
        )
    )
    data["kept"] = set(data.get("kept", []))
    data["symbol_to_strike"] = {
        str(symbol): float(strike)
        for symbol, strike in dict(data.get("symbol_to_strike", {})).items()
    }
    return data


def infer_strike_from_symbol_native(symbol: str) -> float | None:
    value = _L0_RUST.l0_orch_infer_strike_from_symbol(symbol)
    return None if value is None else float(value)


def read_u64_native(buffer: bytes, ptr: int) -> int:
    return int(_L0_RUST.l0_orch_read_u64(buffer, int(ptr)))


def next_trading_day_native(base_day: date) -> date:
    return date.fromisoformat(_L0_RUST.l0_orch_next_trading_day_iso(base_day.isoformat()))


def to_positive_float_native(raw: Any) -> float | None:
    value = _L0_RUST.l0_orch_to_positive_float(raw)
    return None if value is None else float(value)


def normalize_decimal_ratio_native(raw: Any) -> float | None:
    value = _L0_RUST.l0_orch_normalize_decimal_ratio(raw)
    return None if value is None else float(value)


def average_valid_native(values: list[float | None]) -> float | None:
    value = _L0_RUST.l0_orch_average_valid(list(values))
    return None if value is None else float(value)


def select_nearest_chain_item_native(chain_info: list[Any], spot: float) -> Any | None:
    index = _L0_RUST.l0_orch_select_nearest_chain_index(list(chain_info), float(spot))
    if index is None:
        return None
    idx = int(index)
    if idx < 0 or idx >= len(chain_info):
        return None
    return chain_info[idx]


def extract_option_iv_decimal_native(quote: Any) -> float | None:
    value = _L0_RUST.l0_orch_extract_option_iv_decimal(quote)
    return None if value is None else float(value)


def build_symbol_metadata_native(
    chain_info: list[Any],
    *,
    spot: float,
    window: float,
) -> tuple[dict[str, float], dict[str, bool], int]:
    data = dict(_L0_RUST.l0_poller_build_symbol_metadata(list(chain_info), float(spot), float(window)))
    return dict(data["sym_to_strike"]), dict(data["standard_by_symbol"]), int(data["kept"])


def normalize_calc_rows_native(
    results: list[Any],
    *,
    expiry: str,
    tier: str,
    sym_to_strike: dict[str, float],
    standard_by_symbol: dict[str, bool],
) -> list[dict[str, Any]]:
    rows = _L0_RUST.l0_poller_normalize_calc_rows(
        list(results),
        str(expiry),
        str(tier),
        dict(sym_to_strike),
        dict(standard_by_symbol),
    )
    return [dict(row) for row in rows]


def top_open_interest_native(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    return [dict(row) for row in _L0_RUST.l0_poller_top_open_interest(list(rows), int(limit))]

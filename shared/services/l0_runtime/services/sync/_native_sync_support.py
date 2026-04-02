from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.services.l0_runtime._native_extension_loader import load_l0_rust

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "_native_generated"
_L0_RUST = load_l0_rust(
    candidates=[
        _PACKAGE_DIR / "wave7" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave6" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave5" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave4" / "l0_rust.pyd",
        _PACKAGE_DIR / "l0_rust.pyd",
    ],
    module_suffix="l0_rust_wave7_sync_support",
)


def clamp_subscription_cap_native(raw_cap: Any) -> int:
    return int(_L0_RUST.l0_sync_clamp_subscription_cap(raw_cap))


def safe_batch_size_native(max_symbol_weight: Any) -> int:
    return int(_L0_RUST.l0_sync_safe_batch_size(max_symbol_weight))


def split_sync_chunks_native(symbols: list[str]) -> list[list[str]]:
    return [list(chunk) for chunk in _L0_RUST.l0_sync_split_sync_chunks(list(symbols))]


def parse_implied_volatility_native(item: Any) -> float | None:
    value = _L0_RUST.l0_sync_parse_implied_volatility(item)
    return None if value is None else float(value)


def parse_open_interest_native(item: Any) -> int | None:
    value = _L0_RUST.l0_sync_parse_open_interest(item)
    return None if value is None else int(value)


def is_rate_limit_error_native(exc: Exception) -> bool:
    return bool(_L0_RUST.l0_sync_is_rate_limit_error(str(exc)))


def pick_price_repair_candidates_native(
    *,
    batch: list[str],
    eligible_symbols: set[str],
    last_repair_at: dict[str, float],
    now_mono: float,
) -> list[str]:
    return list(
        _L0_RUST.l0_sync_pick_price_repair_candidates(
            list(batch),
            sorted(eligible_symbols),
            dict(last_repair_at),
            float(now_mono),
        )
    )


def apply_repair_rows_native(rows: list[Any], now_mono: float) -> dict[str, Any]:
    data = dict(_L0_RUST.l0_sync_apply_repair_rows(list(rows), float(now_mono)))
    data["updates"] = [dict(item) for item in data.get("updates", [])]
    data["last_repair_at"] = dict(data.get("last_repair_at", {}))
    return data

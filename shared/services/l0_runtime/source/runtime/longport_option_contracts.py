from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any
from ._native_quote_api_support import (
    build_calc_index_contract_native,
    build_option_chain_strike_contract_native,
    build_option_quote_contract_native,
)


def _get(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_trade_status(value: Any) -> int | None:
    code = _to_int(value)
    if code is not None:
        return code
    enum_value = _get(value, "value")
    return _to_int(enum_value)


def _to_decimal_ratio(value: Any) -> float | None:
    parsed = _to_float(value)
    if parsed is None:
        return None
    if parsed < 0:
        return None
    if parsed > 1.0:
        return parsed / 100.0
    return parsed


def _to_iso_date(value: Any) -> str | None:
    text = _to_text(value)
    if text is None:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 8:
        fmt = "%Y%m%d"
    elif len(digits) == 6:
        fmt = "%y%m%d"
    else:
        return None
    try:
        return datetime.strptime(digits, fmt).strftime("%Y-%m-%d")
    except ValueError:
        return None


@dataclass(slots=True)
class OptionExtendContract:
    implied_volatility: str | None = None
    open_interest: int | None = None
    expiry_date: str | None = None
    strike_price: str | None = None
    contract_multiplier: str | None = None
    contract_type: str | None = None
    contract_size: str | None = None
    direction: str | None = None
    historical_volatility: str | None = None
    underlying_symbol: str | None = None


@dataclass(slots=True)
class OptionQuoteContract:
    symbol: str
    last_done: float | None = None
    prev_close: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    timestamp: int | None = None
    volume: int | None = None
    turnover: float | None = None
    trade_status: int | None = None
    option_extend: OptionExtendContract | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    implied_volatility_raw: str | None = None
    implied_volatility_decimal: float | None = None
    expiry_date: str | None = None
    expiry_date_raw: str | None = None
    expiry_date_iso: str | None = None
    strike_price: float | None = None
    strike_price_raw: str | None = None
    contract_multiplier: float | None = None
    contract_type: str | None = None
    contract_size: float | None = None
    direction: str | None = None
    historical_volatility: float | None = None
    historical_volatility_raw: str | None = None
    historical_volatility_decimal: float | None = None
    underlying_symbol: str | None = None


@dataclass(slots=True)
class OptionChainStrikeContract:
    price: float | None = None
    price_raw: str | None = None
    strike_price: float | None = None
    call_symbol: str | None = None
    put_symbol: str | None = None
    standard: bool | None = None


@dataclass(slots=True)
class CalcIndexContract:
    symbol: str
    last_done: float | None = None
    change_val: float | None = None
    change_rate: float | None = None
    volume: int | None = None
    turnover: float | None = None
    expiry_date: str | None = None
    expiry_date_raw: str | None = None
    expiry_date_iso: str | None = None
    strike_price: float | None = None
    strike_price_raw: str | None = None
    premium: float | None = None
    implied_volatility: float | None = None
    implied_volatility_raw: str | None = None
    implied_volatility_decimal: float | None = None
    open_interest: int | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None


def build_option_quote_contract(row: Any) -> OptionQuoteContract:
    data = build_option_quote_contract_native(row)
    option_extend_data = data.get("option_extend")
    option_extend = None
    if isinstance(option_extend_data, dict):
        option_extend = OptionExtendContract(**option_extend_data)
    return OptionQuoteContract(**{**data, "option_extend": option_extend})


def build_option_chain_strike_contract(row: Any) -> OptionChainStrikeContract:
    return OptionChainStrikeContract(**build_option_chain_strike_contract_native(row))


def build_calc_index_contract(row: Any) -> CalcIndexContract:
    return CalcIndexContract(**build_calc_index_contract_native(row))

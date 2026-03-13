from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any


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
    option_extend_src = _get(row, "option_extend")
    implied_raw = (
        _to_text(_get(option_extend_src, "implied_volatility"))
        or _to_text(_get(row, "implied_volatility_raw"))
        or _to_text(_get(row, "implied_volatility"))
    )
    hist_raw = (
        _to_text(_get(option_extend_src, "historical_volatility"))
        or _to_text(_get(row, "historical_volatility_raw"))
        or _to_text(_get(row, "historical_volatility"))
    )
    expiry_raw = (
        _to_text(_get(option_extend_src, "expiry_date"))
        or _to_text(_get(row, "expiry_date_raw"))
        or _to_text(_get(row, "expiry_date"))
    )
    strike_raw = (
        _to_text(_get(option_extend_src, "strike_price"))
        or _to_text(_get(row, "strike_price_raw"))
        or _to_text(_get(row, "strike_price"))
    )
    multiplier_raw = _to_text(_get(option_extend_src, "contract_multiplier")) or _to_text(
        _get(row, "contract_multiplier")
    )
    size_raw = _to_text(_get(option_extend_src, "contract_size")) or _to_text(
        _get(row, "contract_size")
    )
    open_interest = _to_int(_get(row, "open_interest"))
    if open_interest is None:
        open_interest = _to_int(_get(option_extend_src, "open_interest"))

    option_extend = None
    if any(
        value is not None
        for value in (
            implied_raw,
            open_interest,
            expiry_raw,
            strike_raw,
            multiplier_raw,
            _get(option_extend_src, "contract_type"),
            size_raw,
            _get(option_extend_src, "direction"),
            hist_raw,
            _get(option_extend_src, "underlying_symbol"),
        )
    ):
        option_extend = OptionExtendContract(
            implied_volatility=implied_raw,
            open_interest=open_interest,
            expiry_date=expiry_raw,
            strike_price=strike_raw,
            contract_multiplier=multiplier_raw,
            contract_type=_to_text(_get(option_extend_src, "contract_type")) or _to_text(_get(row, "contract_type")),
            contract_size=size_raw,
            direction=_to_text(_get(option_extend_src, "direction")) or _to_text(_get(row, "direction")),
            historical_volatility=hist_raw,
            underlying_symbol=_to_text(_get(option_extend_src, "underlying_symbol")) or _to_text(_get(row, "underlying_symbol")),
        )

    return OptionQuoteContract(
        symbol=_to_text(_get(row, "symbol")) or "",
        last_done=_to_float(_get(row, "last_done")),
        prev_close=_to_float(_get(row, "prev_close")),
        open=_to_float(_get(row, "open")),
        high=_to_float(_get(row, "high")),
        low=_to_float(_get(row, "low")),
        timestamp=_to_int(_get(row, "timestamp")),
        volume=_to_int(_get(row, "volume")),
        turnover=_to_float(_get(row, "turnover")),
        trade_status=_to_trade_status(_get(row, "trade_status")),
        option_extend=option_extend,
        open_interest=open_interest,
        implied_volatility=_to_float(_get(row, "implied_volatility")),
        implied_volatility_raw=implied_raw,
        implied_volatility_decimal=_to_decimal_ratio(implied_raw or _get(row, "implied_volatility")),
        expiry_date=_to_iso_date(expiry_raw),
        expiry_date_raw=expiry_raw,
        expiry_date_iso=_to_iso_date(expiry_raw),
        strike_price=_to_float(strike_raw or _get(row, "strike_price")),
        strike_price_raw=strike_raw,
        contract_multiplier=_to_float(multiplier_raw or _get(row, "contract_multiplier")),
        contract_type=_to_text(_get(option_extend_src, "contract_type")) or _to_text(_get(row, "contract_type")),
        contract_size=_to_float(size_raw or _get(row, "contract_size")),
        direction=_to_text(_get(option_extend_src, "direction")) or _to_text(_get(row, "direction")),
        historical_volatility=_to_float(hist_raw or _get(row, "historical_volatility")),
        historical_volatility_raw=hist_raw,
        historical_volatility_decimal=_to_decimal_ratio(hist_raw or _get(row, "historical_volatility")),
        underlying_symbol=_to_text(_get(option_extend_src, "underlying_symbol")) or _to_text(_get(row, "underlying_symbol")),
    )


def build_option_chain_strike_contract(row: Any) -> OptionChainStrikeContract:
    price_raw = _to_text(_get(row, "price_raw")) or _to_text(_get(row, "price"))
    price = _to_float(_get(row, "price"))
    return OptionChainStrikeContract(
        price=price,
        price_raw=price_raw,
        strike_price=price,
        call_symbol=_to_text(_get(row, "call_symbol")),
        put_symbol=_to_text(_get(row, "put_symbol")),
        standard=_get(row, "standard"),
    )


def build_calc_index_contract(row: Any) -> CalcIndexContract:
    implied_raw = _to_text(_get(row, "implied_volatility_raw")) or _to_text(_get(row, "implied_volatility"))
    expiry_raw = _to_text(_get(row, "expiry_date_raw")) or _to_text(_get(row, "expiry_date"))
    strike_raw = _to_text(_get(row, "strike_price_raw")) or _to_text(_get(row, "strike_price"))
    return CalcIndexContract(
        symbol=_to_text(_get(row, "symbol")) or "",
        last_done=_to_float(_get(row, "last_done")),
        change_val=_to_float(_get(row, "change_val")),
        change_rate=_to_float(_get(row, "change_rate")),
        volume=_to_int(_get(row, "volume")),
        turnover=_to_float(_get(row, "turnover")),
        expiry_date=_to_iso_date(expiry_raw),
        expiry_date_raw=expiry_raw,
        expiry_date_iso=_to_iso_date(expiry_raw),
        strike_price=_to_float(strike_raw or _get(row, "strike_price")),
        strike_price_raw=strike_raw,
        premium=_to_float(_get(row, "premium")),
        implied_volatility=_to_float(_get(row, "implied_volatility")),
        implied_volatility_raw=implied_raw,
        implied_volatility_decimal=_to_decimal_ratio(implied_raw or _get(row, "implied_volatility")),
        open_interest=_to_int(_get(row, "open_interest")),
        delta=_to_float(_get(row, "delta")),
        gamma=_to_float(_get(row, "gamma")),
        theta=_to_float(_get(row, "theta")),
        vega=_to_float(_get(row, "vega")),
        rho=_to_float(_get(row, "rho")),
    )

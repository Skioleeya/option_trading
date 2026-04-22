from __future__ import annotations

from typing import Any

from shared_rust.services import (
    mm_condition_filtered,
    mm_exposure_delta_gamma,
    mm_oi_participation,
    mm_tick_rule_direction,
)

from .constants import (
    OPTION_RE,
    QUADRANT_CALL_ASK,
    QUADRANT_CALL_BID,
    QUADRANT_PUT_ASK,
    QUADRANT_PUT_BID,
    SIDE_ASK,
    SIDE_BID,
    SIDE_MID,
)


def parse_option_type(symbol: str) -> str | None:
    if not symbol:
        return None
    match = OPTION_RE.search(symbol.upper())
    if match is None:
        return None
    return "CALL" if match.group(1) == "C" else "PUT"


def to_positive_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0.0:
        return None
    return parsed


def to_non_negative_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def obj_get(item: object, key: str) -> object | None:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def extract_symbol(item: object) -> str | None:
    raw = obj_get(item, "symbol")
    if raw is None:
        return None
    text = str(raw).strip()
    return text if text else None


def extract_open_interest(item: object) -> int | None:
    direct = to_non_negative_int(obj_get(item, "open_interest"))
    if direct is not None:
        return direct
    option_extend = obj_get(item, "option_extend")
    if option_extend is None:
        return None
    return to_non_negative_int(obj_get(option_extend, "open_interest"))


def extract_level_price(levels: list[object]) -> float | None:
    if not levels:
        return None
    first = levels[0]
    if isinstance(first, dict):
        return to_positive_float(first.get("price"))
    if isinstance(first, (tuple, list)) and first:
        return to_positive_float(first[0])
    return to_positive_float(getattr(first, "price", None))


def extract_trade_price(trade: object) -> float | None:
    if isinstance(trade, dict):
        return to_positive_float(trade.get("price"))
    return to_positive_float(getattr(trade, "price", None))


def extract_trade_volume(trade: object) -> float | None:
    if isinstance(trade, dict):
        volume = trade.get("volume", trade.get("vol"))
    else:
        volume = getattr(trade, "volume", getattr(trade, "vol", None))
    return to_positive_float(volume)


def extract_trade_direction(trade: object) -> int:
    if isinstance(trade, dict):
        raw = trade.get("direction", trade.get("dir"))
    else:
        raw = getattr(trade, "direction", getattr(trade, "dir", None))
    try:
        val = int(raw)
        if val > 0:
            return 1
        if val < 0:
            return -1
        return 0
    except (TypeError, ValueError):
        text = str(raw).upper()
        if "UP" in text:
            return 1
        if "DOWN" in text:
            return -1
        return 0


def extract_trade_type(trade: object) -> str | None:
    raw = obj_get(trade, "trade_type")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def extract_trade_session(trade: object) -> str | None:
    raw = obj_get(trade, "trade_session")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def is_trade_condition_filtered(trade: object) -> bool:
    return bool(mm_condition_filtered(extract_trade_type(trade)))


def tick_rule_direction(
    *,
    price: float,
    bid1: float | None,
    ask1: float | None,
    prev_price: float | None,
    prev_direction: int,
) -> int:
    return int(
        mm_tick_rule_direction(
            float(price),
            bid1=bid1,
            ask1=ask1,
            prev_price=prev_price,
            prev_direction=int(prev_direction),
        )
    )


def oi_participation(size: float, open_interest: int | float | None) -> float:
    oi = float(open_interest or 0.0)
    return float(mm_oi_participation(float(size), oi))


def exposure_delta_gamma(
    *,
    direction: int,
    size: float,
    delta: float | None,
    gamma: float | None,
) -> tuple[float, float]:
    net_delta, net_gamma = mm_exposure_delta_gamma(
        int(direction),
        float(size),
        float(delta or 0.0),
        float(gamma or 0.0),
    )
    return float(net_delta), float(net_gamma)


def classify_trade_side(
    *,
    price: float | None,
    bid1: float | None,
    ask1: float | None,
    epsilon: float = 1e-6,
) -> str:
    if price is None or price <= 0.0:
        return SIDE_MID
    if ask1 is not None and price >= (ask1 - epsilon):
        return SIDE_ASK
    if bid1 is not None and price <= (bid1 + epsilon):
        return SIDE_BID
    return SIDE_MID


def quadrant_for(option_type: str | None, side: str) -> str | None:
    if option_type == "PUT" and side == SIDE_ASK:
        return QUADRANT_PUT_ASK
    if option_type == "CALL" and side == SIDE_BID:
        return QUADRANT_CALL_BID
    if option_type == "PUT" and side == SIDE_BID:
        return QUADRANT_PUT_BID
    if option_type == "CALL" and side == SIDE_ASK:
        return QUADRANT_CALL_ASK
    return None

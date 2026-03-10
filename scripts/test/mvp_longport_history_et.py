"""
MVP: Pull SPY 1m history candlesticks from Longbridge and normalize timestamps to ET.

Usage:
  python scripts/test/mvp_longport_history_et.py
  python scripts/test/mvp_longport_history_et.py --symbol SPY.US --count 10
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from longport.openapi import AdjustType, Config, Period, QuoteContext

from shared.config import settings


ET = ZoneInfo("America/New_York")


@dataclass
class CandleTimeView:
    raw: datetime
    et: datetime
    utc: datetime


def to_et(ts: datetime) -> datetime:
    """Normalize Longbridge candle timestamp to America/New_York."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=ET)
    return ts.astimezone(ET)


def build_context() -> QuoteContext:
    cfg = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
        http_url=settings.longport_http_url,
        quote_ws_url=settings.longport_quote_ws_url,
        trade_ws_url=settings.longport_trade_ws_url,
    )
    return QuoteContext(cfg)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MVP check for Longbridge history-candlestick timestamp timezone.")
    p.add_argument("--symbol", default="SPY.US", help="Longbridge symbol, e.g. SPY.US")
    p.add_argument("--count", type=int, default=5, help="Number of bars to pull (recommended <= 20 for MVP)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    count = max(1, min(int(args.count), 200))
    symbol = str(args.symbol).strip().upper()

    ctx = build_context()
    bars = ctx.history_candlesticks_by_offset(
        symbol,
        Period.Min_1,
        AdjustType.NoAdjust,
        True,
        count,
    )

    print(f"symbol={symbol} requested={count} returned={len(bars)}")
    if not bars:
        print("no bars returned")
        return 1

    print("idx | raw_timestamp              | et_timestamp                   | utc_timestamp")
    print("----+----------------------------+--------------------------------+-------------------------------")
    for i, bar in enumerate(bars, start=1):
        raw = getattr(bar, "timestamp", None)
        if not isinstance(raw, datetime):
            print(f"{i:>3} | invalid timestamp type: {type(raw)}")
            return 2
        et_ts = to_et(raw)
        utc_ts = et_ts.astimezone(timezone.utc)
        print(
            f"{i:>3} | {str(raw):<26} | {et_ts.isoformat():<30} | {utc_ts.isoformat()}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

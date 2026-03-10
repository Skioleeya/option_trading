from __future__ import annotations

from datetime import date
from typing import Iterable

from tools.momentum_calibration.models import Direction, FeatureRow, KlineBar


def direction_from_return(value: float, *, epsilon: float = 1e-12) -> Direction:
    if value > epsilon:
        return "BULLISH"
    if value < -epsilon:
        return "BEARISH"
    return "NEUTRAL"


def build_feature_rows(
    bars: Iterable[KlineBar],
    *,
    horizon_minutes: int = 5,
) -> list[FeatureRow]:
    seq = sorted(list(bars), key=lambda b: b.ts_et)
    out: list[FeatureRow] = []
    if len(seq) <= horizon_minutes + 1:
        return out

    for i in range(1, len(seq) - horizon_minutes):
        prev_bar = seq[i - 1]
        cur_bar = seq[i]
        fut_bar = seq[i + horizon_minutes]
        if prev_bar.close <= 0.0 or cur_bar.close <= 0.0:
            continue

        spot_roc_1m = (cur_bar.close / prev_bar.close) - 1.0
        fwd_ret = (fut_bar.close / cur_bar.close) - 1.0 if cur_bar.close > 0.0 else 0.0

        out.append(
            FeatureRow(
                ts_et=cur_bar.ts_et,
                close=cur_bar.close,
                spot_roc_1m=spot_roc_1m,
                fwd_ret_5m=fwd_ret,
                label_direction=direction_from_return(fwd_ret),
            )
        )
    return out


def slice_last_trade_days(rows: Iterable[FeatureRow], *, end_date: date, trade_days: int) -> list[FeatureRow]:
    seq = [r for r in rows if r.ts_et.date() <= end_date]
    if not seq:
        return []
    dates = sorted({r.ts_et.date() for r in seq})
    chosen = set(dates[-max(1, trade_days) :])
    return [r for r in seq if r.ts_et.date() in chosen]


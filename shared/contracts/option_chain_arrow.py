"""Neutral Arrow contract for L0 -> L1 option-chain pass-through."""

from __future__ import annotations

from typing import Any

import pyarrow as pa

OPTION_CHAIN_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("strike", pa.float64()),
        pa.field("is_call", pa.bool_()),
        pa.field("bid", pa.float64()),
        pa.field("ask", pa.float64()),
        pa.field("iv", pa.float64()),
        pa.field("volume", pa.float64()),
        pa.field("current_volume", pa.float64()),
        pa.field("turnover", pa.float64()),
        pa.field("open_interest", pa.float64()),
        pa.field("contract_multiplier", pa.float64()),
    ]
)


def dicts_to_record_batch(chain_snapshot: list[dict[str, Any]]) -> pa.RecordBatch:
    """Convert normalized L0 rows into the shared Arrow option-chain contract."""
    symbols: list[str] = []
    strikes: list[float] = []
    is_calls: list[bool] = []
    bids: list[float] = []
    asks: list[float] = []
    ivs: list[float] = []
    volumes: list[float] = []
    current_volumes: list[float] = []
    turnovers: list[float] = []
    open_interests: list[float] = []
    multipliers: list[float] = []

    for entry in chain_snapshot:
        symbols.append(str(entry.get("symbol", "")))
        strikes.append(float(entry.get("strike", 0.0) or 0.0))
        opt_type = str(entry.get("type", "CALL")).upper()
        is_calls.append(opt_type in {"CALL", "C"})
        bids.append(float(entry.get("bid", 0.0) or 0.0))
        asks.append(float(entry.get("ask", 0.0) or 0.0))

        iv_value = entry.get("iv")
        if iv_value is None:
            iv_value = entry.get("implied_volatility", 0.0)
        ivs.append(float(iv_value or 0.0))

        volumes.append(float(entry.get("volume", 0.0) or 0.0))
        current_volumes.append(float(entry.get("current_volume", 0.0) or 0.0))
        turnovers.append(float(entry.get("turnover", 0.0) or 0.0))
        open_interests.append(float(entry.get("open_interest", 0.0) or 0.0))
        multipliers.append(float(entry.get("contract_multiplier", 100.0) or 100.0))

    arrays = [
        pa.array(symbols, type=pa.string()),
        pa.array(strikes, type=pa.float64()),
        pa.array(is_calls, type=pa.bool_()),
        pa.array(bids, type=pa.float64()),
        pa.array(asks, type=pa.float64()),
        pa.array(ivs, type=pa.float64()),
        pa.array(volumes, type=pa.float64()),
        pa.array(current_volumes, type=pa.float64()),
        pa.array(turnovers, type=pa.float64()),
        pa.array(open_interests, type=pa.float64()),
        pa.array(multipliers, type=pa.float64()),
    ]
    return pa.RecordBatch.from_arrays(arrays, schema=OPTION_CHAIN_SCHEMA)


def ensure_record_batch(data: list[dict[str, Any]] | pa.RecordBatch) -> pa.RecordBatch:
    """Return a RecordBatch regardless of whether caller passed rows or Arrow."""
    if isinstance(data, pa.RecordBatch):
        return data
    return dicts_to_record_batch(data)

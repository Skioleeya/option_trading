"""PyArrow Schema and conversion utilities for L0 -> L1 zero-copy data passing.

Defines the native Apache Arrow schema for Option Chain snapshots to be used 
across the system, facilitating zero-copy sharing and vectorized computations.
"""
from typing import Any, List, Union

import pyarrow as pa

# Native schema for Options Data. Ensures predictable typing when converting.
OPTION_CHAIN_SCHEMA = pa.schema([
    pa.field("symbol", pa.string()),
    pa.field("strike", pa.float64()),
    pa.field("is_call", pa.bool_()),
    pa.field("bid", pa.float64()),
    pa.field("ask", pa.float64()),
    pa.field("iv", pa.float64()),
    pa.field("volume", pa.float64()),
    pa.field("open_interest", pa.float64()),
    pa.field("contract_multiplier", pa.float64()),
])


def dicts_to_record_batch(chain_snapshot: List[dict[str, Any]]) -> pa.RecordBatch:
    """Fallback utility to convert legacy list[dict] data into Arrow RecordBatch.
    
    Used only when L0 is still feeding legacy python types to L1. Maps dictionary
    keys to the strict OPTION_CHAIN_SCHEMA.
    """
    symbols = []
    strikes = []
    is_calls = []
    bids = []
    asks = []
    ivs = []
    volumes = []
    ois = []
    mults = []

    for entry in chain_snapshot:
        symbols.append(entry.get("symbol", ""))
        strikes.append(float(entry.get("strike", 0.0)))
        
        opt_type = entry.get("type", "CALL").upper()
        # Both "CALL" and "C" signify a Call option
        is_calls.append(opt_type in ("CALL", "C"))
        
        bids.append(float(entry.get("bid", 0.0) or 0.0))
        asks.append(float(entry.get("ask", 0.0) or 0.0))
        
        iv_val = entry.get("iv")
        if iv_val is None:
            iv_val = entry.get("implied_volatility", 0.0)
        ivs.append(float(iv_val or 0.0))
        
        volumes.append(float(entry.get("volume", 0.0) or 0.0))
        ois.append(float(entry.get("open_interest", 0.0)))
        mults.append(float(entry.get("contract_multiplier", 100.0)))

    arrays = [
        pa.array(symbols, type=pa.string()),
        pa.array(strikes, type=pa.float64()),
        pa.array(is_calls, type=pa.bool_()),
        pa.array(bids, type=pa.float64()),
        pa.array(asks, type=pa.float64()),
        pa.array(ivs, type=pa.float64()),
        pa.array(volumes, type=pa.float64()),
        pa.array(ois, type=pa.float64()),
        pa.array(mults, type=pa.float64()),
    ]
    
    return pa.RecordBatch.from_arrays(arrays, schema=OPTION_CHAIN_SCHEMA)

def ensure_record_batch(data: Union[List[dict[str, Any]], pa.RecordBatch]) -> pa.RecordBatch:
    """Ensure the incoming data is a PyArrow RecordBatch."""
    if isinstance(data, pa.RecordBatch):
        return data
    return dicts_to_record_batch(data)

import sys
import os
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Add backend root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from longport.openapi import QuoteContext, Config, CalcIndex
from app.config import settings

async def test_threshold():
    print(">>> THRESHOLD PROBE: 100 Symbols x 10 Calls (1Hz)")
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token
    )
    ctx = QuoteContext(config)

    base_date = datetime.now(ZoneInfo("US/Eastern")).date()
    chain_info = ctx.option_chain_info_by_date("SPY.US", base_date)
    test_symbols = []
    for info in chain_info[:50]:
        test_symbols.append(info.call_symbol)
        test_symbols.append(info.put_symbol)

    print(f"Testing with unique pool of {len(test_symbols)} symbols.")
    
    start_time = time.time()
    total_requested = 0
    
    for i in range(1, 11):
        print(f"[{time.time()-start_time:.1f}s] Call #{i}. Total units attempted: {total_requested + len(test_symbols)}")
        try:
            ctx.calc_indexes(test_symbols, [CalcIndex.Delta])
            total_requested += len(test_symbols)
        except Exception as e:
            print(f"!!! [FAILURE] at {total_requested} units. Error: {e}")
            break
        await asyncio.sleep(1.0)
    
    print(f"\nFinal Total Units Request: {total_requested}")
    if total_requested >= 1000:
        print(">>> RESULT: Periodic REPETITION allowed for 100 symbols (UNIQUE based).")
    else:
        print(">>> RESULT: REPETITION failed (TOTAL-UNIT based).")

if __name__ == "__main__":
    asyncio.run(test_threshold())

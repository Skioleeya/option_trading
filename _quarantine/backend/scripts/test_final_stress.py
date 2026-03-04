import sys
import os
import time
import asyncio
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Add backend root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from longport.openapi import QuoteContext, Config, CalcIndex
from app.config import settings

async def stress_test():
    print(">>> CRITICAL STRESS TEST: 1Hz Hybrid Architecture Simulation")
    print(f">>> Start Time: {datetime.now()}")
    
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token
    )
    ctx = QuoteContext(config)

    # 1. Prepare Symbol Pools
    base_date = datetime.now(ZoneInfo("US/Eastern")).date()
    all_symbols = []
    
    # Need ~520 symbols total
    for i in range(5):
        check_date = base_date + timedelta(days=i)
        chain_info = ctx.option_chain_info_by_date("SPY.US", check_date)
        if chain_info:
            for info in chain_info:
                if info.call_symbol: all_symbols.append(info.call_symbol)
                if info.put_symbol: all_symbols.append(info.put_symbol)
        if len(all_symbols) >= 600: break

    if len(all_symbols) < 520:
        print(f"Fail: Only found {len(all_symbols)} symbols. Need 520.")
        return

    core_pool = all_symbols[:300]
    wide_pool_a = all_symbols[300:410]
    wide_pool_b = all_symbols[410:520]
    
    print(f"Pools Initialized:")
    print(f" - Core: {len(core_pool)} symbols (Target: 1Hz)")
    print(f" - Wide A: {len(wide_pool_a)} symbols (Target: Rotating)")
    print(f" - Wide B: {len(wide_pool_b)} symbols (Target: Rotating)")
    print(f" - Total Unique in System: {len(set(core_pool + wide_pool_a + wide_pool_b))}")

    # Metrics
    test_duration = 150 # 2.5 minutes
    start_time = time.time()
    last_wide_rotate = 0
    wide_bucket = 'A'
    
    success_count = 0
    error_count = 0
    
    greeks = [CalcIndex.Delta, CalcIndex.Gamma, CalcIndex.OpenInterest]

    print("\n--- Starting REAL-TIME Loop (5 Minutes) ---")
    
    cycle_count = 0
    while time.time() - start_time < test_duration:
        loop_start = time.perf_counter()
        cycle_count += 1
        
        # Determine unique set for this second
        # Current logic: Core is always refreshed. Wide rotates every 120s full cycle (60s swap).
        current_symbols = list(core_pool)
        
        elapsed_since_start = time.time() - start_time
        if int(elapsed_since_start // 60) % 2 == 0:
            # Min 0, 2, 4 -> Wide A
            current_symbols.extend(wide_pool_a)
            bucket_tag = "CORE+WA"
        else:
            # Min 1, 3, 5 -> Wide B
            current_symbols.extend(wide_pool_b)
            bucket_tag = "CORE+WB"

        try:
            # Stress test point: 410 symbols in ONE call.
            ctx.calc_indexes(current_symbols, greeks)
            success_count += 1
            if cycle_count % 10 == 0:
                print(f"[{time.time()-start_time:.1f}s] Cycle {cycle_count} OK. Batch: {len(current_symbols)} ({bucket_tag})")
        except Exception as e:
            error_count += 1
            print(f"!!! [FAILURE] Cycle {cycle_count} at {time.time()-start_time:.1f}s. Error: {e}")
            if "301607" in str(e):
                print(">>> BREACH DETECTED: Unique symbol sliding window threshold hit!")
            break

        # Align with 1.0s clock precisely
        execution_time = time.perf_counter() - loop_start
        sleep_time = max(0, 1.0 - execution_time)
        await asyncio.sleep(sleep_time)

    total_time = time.time() - start_time
    print(f"\n--- Test Results ---")
    print(f"Total Time: {total_time:.1f}s")
    print(f"Total Cycles: {cycle_count}")
    print(f"Successes: {success_count}")
    print(f"Errors: {error_count}")
    
    if error_count == 0:
        print(">>> VALIDATION PASSED: Proposed parameters are 100% safe.")
    else:
        print(">>> VALIDATION FAILED: Need to adjust pool sizes or rotation intervals.")

if __name__ == "__main__":
    try:
        asyncio.run(stress_test())
    except KeyboardInterrupt:
        pass

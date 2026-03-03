import asyncio
import logging
import sys
import os
from datetime import datetime, date, timedelta
from typing import Any

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from longport.openapi import QuoteContext, Config, Period, AdjustType
from app.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_history_kline")

async def test_kline(ctx: QuoteContext, symbol: str, start_date: date, end_date: date):
    logger.info(f"--- Testing Historical K-Line for {symbol} ({start_date} to {end_date}) ---")
    try:
        # Request 1-minute K-lines
        candlesticks = ctx.history_candlesticks_by_date(
            symbol, 
            Period.Min_1, 
            AdjustType.NoAdjust, 
            start_date, 
            end_date
        )
        if candlesticks:
            logger.info(f"[SUCCESS] Retrieved {len(candlesticks)} K-lines for {symbol}")
            first = candlesticks[0]
            last = candlesticks[-1]
            logger.info(f"  First: Time={first.timestamp}, O={first.open}")
            logger.info(f"  Last:  Time={last.timestamp}, C={last.close}")
        else:
            logger.warning(f"[EMPTY] No historical data returned for {symbol}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch history for {symbol}: {e}")

async def run_test():
    try:
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        ctx = QuoteContext(config)

        # 1. SPY (Active)
        end = date.today()
        start = end - timedelta(days=2)
        await test_kline(ctx, "SPY.US", start, end)

        # 2. Get a currently active option symbol
        spot_sym = "SPY.US"
        chains = ctx.option_chain_info_by_date(spot_sym, end)
        if chains:
            active_sym = chains[0].call_symbol
            logger.info(f"Using active symbol: {active_sym}")
            await test_kline(ctx, active_sym, start, end)
        
        # 3. Attempt to fetch an expired option symbol
        # Today is 2026-03-02 (Monday). Friday was 2026-02-27.
        # Format: SPYYYMMDDC[Strike*1000]
        # Trying strike 680 (Assuming price was near this)
        expired_sym = "SPY260227C680000.US" 
        exp_start = date(2026, 2, 27)
        exp_end = date(2026, 2, 27)
        logger.info(f"Attempting to fetch expired symbol: {expired_sym}")
        await test_kline(ctx, expired_sym, exp_start, exp_end)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_test())
